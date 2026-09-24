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
update swasthyalens_private.explanation_budget set gemini_attempts=19 where id;
create temporary table gemini_budget_before as select reserved_cents from swasthyalens_private.explanation_budget;
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

 input:=input||jsonb_build_object('idempotency_key',gen_random_uuid(),'provider','gemini');
 result:=public.explanation_call('request',input,worker);
 saved:=(result->'record'->>'id')::uuid;
 perform pg_temp.check_parameter(result->>'evaluation_attempt'='20','durable final Gemini reservation');
 perform pg_temp.check_parameter(result->>'reserved_cents'='0','Gemini never consumes paid budget');
 perform pg_temp.check_parameter(result->'record'->>'model'='gemini-3.8-flash','exact Gemini model');
 state:=public.explanation_call('request',input,worker);
 perform pg_temp.check_parameter(state->>'created'='false' and state->>'evaluation_attempt'='0' and state->'record'->>'id'=saved::text,'replay does not reserve');
 perform public.explanation_call('finish',input||jsonb_build_object('id',saved,'error_category','invalid','duration_ms',1),worker);
 -- The failed reservation cannot be recovered through a fresh key.
 begin
  perform public.explanation_call('request',input||jsonb_build_object('idempotency_key',gen_random_uuid()),worker);
  raise exception 'Expected Gemini budget denial';
 exception when sqlstate 'P0001' then
  if sqlerrm<>'explanation_budget' then raise; end if;
 end;
end; $$;
reset role;
select pg_temp.check_parameter((select reserved_cents from swasthyalens_private.explanation_budget)=(select reserved_cents from gemini_budget_before),'historical paid ledger unchanged');
select pg_temp.deny_parameter(format('update public.report_explanations set model=%L where report_id=%L','gpt-5.6-terra',report),'23514') from parameter_test_context where label='A';
update public.reports set status='deleting' where id=(select report from parameter_test_context where label='A');
select swasthyalens_private.explanation_cleanup();
select pg_temp.check_parameter(not exists(select 1 from public.report_explanations where report_id=(select report from parameter_test_context where label='A')),'report deletion removes Gemini output');
select pg_temp.check_parameter((select gemini_attempts=20 from swasthyalens_private.explanation_budget),'failure, deletion and cleanup do not refund attempts');
select pg_temp.check_parameter(not has_column_privilege('authenticated','swasthyalens_private.explanation_budget','gemini_attempts','UPDATE'),'clients cannot reset attempts');
select pg_temp.check_parameter((select relrowsecurity and relforcerowsecurity from pg_class where oid='swasthyalens_private.explanation_budget'::regclass),'attempt counter forced RLS');
rollback;
