-- Development-only, complete rollback transaction. No Storage objects or real users change.
begin;
set local statement_timeout='30s';
set local lock_timeout='5s';
create temporary table parameter_test_context(label text primary key, owner uuid default gen_random_uuid(),
 session uuid default gen_random_uuid(), report uuid default gen_random_uuid(), source uuid default gen_random_uuid(), run uuid, candidate uuid, second uuid) on commit drop;
insert into parameter_test_context(label) values('A'),('B');
grant select,update on parameter_test_context to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
select owner,'authenticated','authenticated',owner::text||'@phase5.invalid',now(),now(),now() from parameter_test_context;
insert into auth.sessions(id,user_id,created_at,updated_at)
select session,owner,now()-interval '5 minutes',now() from parameter_test_context;
insert into public.reports(id,user_id,idempotency_key,storage_path,original_filename,media_type,size_bytes,sha256,status)
select report,owner,gen_random_uuid(),owner::text||'/'||report::text||'/'||gen_random_uuid()::text||'.pdf',
 'synthetic.pdf','application/pdf',100,repeat('a',64),'uploaded' from parameter_test_context;
insert into public.report_processing_runs(id,report_id,idempotency_key,source_sha256,attempt,status,finished_at,processor,page_count)
select source,report,gen_random_uuid(),repeat('a',64),1,'completed',now(),'synthetic',1 from parameter_test_context;
insert into public.report_pages(run_id,page_number,content)
select source,1,'{"text":"Test | Result\nSynthetic | 5","method":"native_text"}' from parameter_test_context;
update swasthyalens_private.processing_key set sha256=encode(extensions.digest(repeat('synthetic',8),'sha256'),'hex');
create function pg_temp.check_parameter(ok boolean,label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
create function pg_temp.deny_parameter(statement text,expected text) returns void language plpgsql as $$
begin
 begin execute statement;
 exception when others then if sqlstate=expected then return; end if;
 raise exception 'Unexpected SQLSTATE %, expected %',sqlstate,expected; end;
 raise exception 'Expected denial did not occur';
end; $$;
set local role authenticated;
do $$
declare actor record; result jsonb; state jsonb; input jsonb; saved uuid; i integer;
 worker text:=repeat('synthetic',8);
 payload jsonb:='[{"page_number":1,"source_text":"Synthetic | 5","source_start":14,"source_end":27,"source_method":"native_text","certainty":"needs_review","fields":{"original_label":"Synthetic","raw_value":"5.00","original_unit":"mg/dL","value_kind":"numeric","numeric_value":"5.00"}}]';
begin
 select * into actor from pg_temp.parameter_test_context where label='A';
 perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
 result:=public.parameter_request(actor.report,actor.source,gen_random_uuid(),'v1','v1',worker);
 perform public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker);
 select id into actor.candidate from public.report_parameter_candidates where run_id=(result->'run'->>'id')::uuid;
 perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),0,'confirmed',null,worker);
 input:=jsonb_build_object('report_id',actor.report);
 perform public.observation_call('publish',input||jsonb_build_object('candidate_id',actor.candidate,'expected_revision',1),worker);
 state:=public.explanation_call('state',input,worker);
 perform public.explanation_call('enroll_synthetic',input||jsonb_build_object('fixture_sha256',repeat('a',64),'expected_evidence',state->'evidence'),worker);
 for i in 1..3 loop
  result:=public.explanation_call('request',input||jsonb_build_object('idempotency_key',gen_random_uuid(),'provider','mock-test'),worker);
  saved:=(result->'record'->>'id')::uuid;
  perform public.explanation_call('finish',input||jsonb_build_object('id',saved,'error_category','timeout','duration_ms',1),worker);
 end loop;
 perform pg_temp.deny_parameter(format('select public.explanation_call(''request'',%L,%L)',input||jsonb_build_object('idempotency_key',gen_random_uuid(),'provider','mock-test'),worker),'P0001');
end; $$;
reset role;
-- These changes affect rollback-only fake-user fixtures and a rolled-back budget snapshot.
update swasthyalens_private.explanation_attempts set created_at=now()-interval '2 minutes' where user_id=(select owner from parameter_test_context where label='A');
update swasthyalens_private.explanation_budget set reserved_cents=500 where id;
set local role authenticated;
do $$
declare actor record; worker text:=repeat('synthetic',8); input jsonb; rejected boolean:=false;
begin
 select * into actor from pg_temp.parameter_test_context where label='A'; input:=jsonb_build_object('report_id',actor.report,'idempotency_key',gen_random_uuid(),'provider','openai');
 begin perform public.explanation_call('request',input,worker);
 exception when sqlstate 'P0001' then rejected:=sqlerrm='explanation_budget'; end;
 perform pg_temp.check_parameter(rejected,'five dollar hard stop');
end; $$;
reset role;
insert into swasthyalens_private.explanation_attempts(id,user_id,created_at)
select gen_random_uuid(),owner,now()-interval '2 minutes' from parameter_test_context cross join generate_series(1,17) where label='A';
set local role authenticated;
do $$
declare actor record; worker text:=repeat('synthetic',8); input jsonb; rejected boolean:=false;
begin
 select * into actor from pg_temp.parameter_test_context where label='A'; input:=jsonb_build_object('report_id',actor.report,'idempotency_key',gen_random_uuid(),'provider','mock-test');
 begin perform public.explanation_call('request',input,worker);
 exception when sqlstate 'P0001' then rejected:=sqlerrm='explanation_rate_limit'; end;
 perform pg_temp.check_parameter(rejected,'daily rate limit persists separately from records');
end; $$;
reset role;
delete from auth.sessions where id=(select session from parameter_test_context where label='A');
set local role authenticated;
select pg_temp.check_parameter(not exists(select 1 from public.report_explanations),'revoked session cannot read');
select pg_temp.deny_parameter(format('select public.explanation_call(''state'',%L,%L)',jsonb_build_object('report_id',report),repeat('synthetic',8)),'28000') from parameter_test_context where label='A';
rollback;
