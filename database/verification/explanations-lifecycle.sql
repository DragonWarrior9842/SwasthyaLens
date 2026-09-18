-- Development-only, complete rollback transaction. No Storage objects or real users change.
begin;
-- Isolate budget assertions inside this full rollback transaction only.
update swasthyalens_private.explanation_budget set reserved_cents=0 where id;
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
declare actor record; other_actor record; result jsonb; state jsonb; generation jsonb;
 key uuid; worker text:=repeat('synthetic',8); input jsonb; saved uuid;
 payload jsonb:='[{"page_number":1,"source_text":"Synthetic | 5","source_start":14,"source_end":27,"source_method":"native_text","certainty":"needs_review","fields":{"original_label":"Synthetic","raw_value":"5.00","original_unit":"mg/dL","value_kind":"numeric","numeric_value":"5.00"}}]';
begin
 for actor in select * from pg_temp.parameter_test_context order by label loop
  select * into other_actor from pg_temp.parameter_test_context where label<>actor.label;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
  input:=jsonb_build_object('report_id',actor.report);
  state:=public.explanation_call('state',input,worker);
  perform pg_temp.check_parameter(state->'evidence'='[]' and not (state->>'evaluation_enrolled')::boolean,'empty evidence excluded');
  perform pg_temp.deny_parameter(format('select public.explanation_call(''state'',%L,%L)',jsonb_build_object('report_id',other_actor.report),worker),'P0001');
  perform pg_temp.deny_parameter(format('select public.explanation_call(''state'',%L,%L)',input,'wrong-worker'),'42501');
  result:=public.parameter_request(actor.report,actor.source,gen_random_uuid(),'v1','v1',worker);
  perform public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker);
  select id into actor.candidate from public.report_parameter_candidates where run_id=(result->'run'->>'id')::uuid;
  perform pg_temp.check_parameter(public.explanation_call('state',input,worker)->'evidence'='[]','unreviewed excluded');
  perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),0,'confirmed',null,worker);
  perform pg_temp.check_parameter(public.explanation_call('state',input,worker)->'evidence'='[]','review without publication excluded');
  perform public.observation_call('publish',input||jsonb_build_object('candidate_id',actor.candidate,'expected_revision',1),worker);
  state:=public.explanation_call('state',input,worker);
  perform pg_temp.check_parameter(jsonb_array_length(state->'evidence')=1,'one authorized evidence');
  key:=gen_random_uuid();
  perform pg_temp.deny_parameter(format('select public.explanation_call(''request'',%L,%L)',input||jsonb_build_object('idempotency_key',key,'provider','openai'),worker),'P0001');
  perform public.explanation_call('enroll_synthetic',input||jsonb_build_object('fixture_sha256',repeat('a',64),'expected_evidence',state->'evidence'),worker);
  generation:=public.explanation_call('request',input||jsonb_build_object('idempotency_key',key,'provider','openai'),worker);
  saved:=(generation->'record'->>'id')::uuid;
  update pg_temp.parameter_test_context set second=saved,candidate=actor.candidate where label=actor.label;
  perform pg_temp.check_parameter((generation->>'created')::boolean and (generation->>'reserved_cents')::int=25,'atomic reservation');
  generation:=public.explanation_call('request',input||jsonb_build_object('idempotency_key',key,'provider','openai'),worker);
  perform pg_temp.check_parameter(not (generation->>'created')::boolean and (generation->'record'->>'id')::uuid=saved,'idempotent no second charge');
  perform pg_temp.deny_parameter(format('select public.explanation_call(''request'',%L,%L)',input||jsonb_build_object('idempotency_key',gen_random_uuid(),'provider','openai'),worker),'P0001');
  generation:=public.explanation_call('finish',input||jsonb_build_object('id',saved,'output',jsonb_build_object('scope','educational','items',jsonb_build_array(jsonb_build_object('fact',state->'evidence'->0))),'input_tokens',1,'output_tokens',1,'duration_ms',1),worker);
  perform pg_temp.check_parameter(generation->'record'->>'status'='ready','finished ready');
  generation:=public.explanation_call('request',input||jsonb_build_object('idempotency_key',gen_random_uuid(),'provider','openai'),worker);
  perform pg_temp.check_parameter(not (generation->>'created')::boolean,'unchanged ready reuse');
  perform pg_temp.check_parameter((select count(*)=1 from public.report_explanations),'RLS only owned row');
  perform pg_temp.deny_parameter('delete from public.report_explanations','42501');
  perform pg_temp.deny_parameter('select * from swasthyalens_private.explanation_budget','42501');
  perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),1,'corrected','{"original_label":"Synthetic","raw_value":"5.01","original_unit":"mmol/L"}',worker);
  generation:=public.explanation_call('state',input,worker);
  perform pg_temp.check_parameter(generation->'record'->>'status'='stale' and generation->'record'->'output'='null' and generation->'record'->'evidence'='[]','correction erases stale output and evidence');
  perform pg_temp.check_parameter(not (generation->>'evaluation_enrolled')::boolean,'correction revokes enrollment');
  perform public.observation_call('publish',input||jsonb_build_object('candidate_id',actor.candidate,'expected_revision',2),worker);
  state:=public.explanation_call('state',input,worker);
  perform public.explanation_call('enroll_synthetic',input||jsonb_build_object('fixture_sha256',repeat('a',64),'expected_evidence',state->'evidence'),worker);
  generation:=public.explanation_call('request',input||jsonb_build_object('idempotency_key',gen_random_uuid(),'provider','mock-test'),worker);
  saved:=(generation->'record'->>'id')::uuid;
  perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),2,'rejected',null,worker);
  generation:=public.explanation_call('finish',input||jsonb_build_object('id',saved,'error_category','timeout','duration_ms',10),worker);
  perform pg_temp.check_parameter(generation->'record'->>'status'='stale','correction during generation cannot resurrect output');
 end loop;
end; $$;
reset role;
select pg_temp.check_parameter((select reserved_cents=50 from swasthyalens_private.explanation_budget),'permanent reservations including stale');
update public.report_explanations set expires_at=now()-interval '1 second' where user_id=(select owner from parameter_test_context where label='A');
select swasthyalens_private.explanation_cleanup();
select pg_temp.check_parameter(not exists(select 1 from public.report_explanations where user_id=(select owner from parameter_test_context where label='A')),'physical expiry');
update public.reports set status='deleting' where id in(select report from parameter_test_context);
select pg_temp.check_parameter(not exists(select 1 from public.report_explanations where user_id in(select owner from parameter_test_context)),'physical deletion');
select pg_temp.check_parameter((select reserved_cents=50 from swasthyalens_private.explanation_budget),'no budget refund on deletion');
select pg_temp.check_parameter(exists(select 1 from cron.job where jobname='swasthyalens-explanation-retention' and active),'scheduled retention active');
rollback;
