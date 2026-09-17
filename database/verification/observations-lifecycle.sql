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
declare actor record; other_actor record; result jsonb; key uuid; worker text:=repeat('synthetic',8);
 payload jsonb:='[{"page_number":1,"source_text":"Synthetic | 5","source_start":14,"source_end":27,"source_method":"native_text","certainty":"needs_review","fields":{"original_label":"Synthetic","raw_value":"5.00","original_unit":"mg/dL","value_kind":"numeric","numeric_value":"5.00"}}]';
 published jsonb; oid uuid; mid uuid; input jsonb; response jsonb;
begin
 for actor in select * from pg_temp.parameter_test_context order by label loop
  select * into other_actor from pg_temp.parameter_test_context where label<>actor.label;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
  result:=public.parameter_request(actor.report,actor.source,gen_random_uuid(),'v1','v1',worker);
  perform public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker);
  select id into actor.candidate from public.report_parameter_candidates where run_id=(result->'run'->>'id')::uuid;
  input:=jsonb_build_object('report_id',actor.report,'candidate_id',actor.candidate,'expected_revision',1);
  perform pg_temp.deny_parameter(format('select public.observation_call(''publish'',%L,%L)',input,worker),'P0001');
  perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),0,'confirmed',null,worker);
  published:=public.observation_call('publish',input,worker); oid:=(published->>'id')::uuid;
  perform pg_temp.check_parameter(published->'current'->>'status'='active' and published->'current'->>'measurement_date' is null,'reviewed publication without fabricated date');
  perform pg_temp.check_parameter(public.observation_call('publish',input,worker)=published,'exact publication replay');
  perform pg_temp.deny_parameter(format('select public.observation_call(''publish'',%L,%L)',input||'{"measurement_date":"2020-01-01"}',worker),'P0001');
  perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),1,'corrected','{"original_label":"Synthetic","raw_value":"5.01","original_unit":"mmol/L"}',worker);
  response:=public.observation_call('get',jsonb_build_object('id',oid),worker);
  perform pg_temp.check_parameter(response->'current'->>'status'='superseded' and response->'current'->'fields'->>'raw_value'='5.00','immutable snapshot invalidated atomically');
  perform pg_temp.deny_parameter(format('select public.observation_call(''publish'',%L,%L)',input,worker),'P0001');
  input:=input||'{"expected_revision":2,"measurement_date":"2020-01-01"}';
  response:=public.observation_call('publish',input,worker);
  perform pg_temp.check_parameter(response->>'id'=oid::text and jsonb_array_length(response->'revisions')=2 and response->'current'->'fields'->>'original_unit'='mmol/L','new active revision keeps units separate');
  perform public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),2,'rejected',null,worker);
  response:=public.observation_call('list','{}',worker);
  perform pg_temp.check_parameter(jsonb_array_length(response->'items')=0,'rejected history excluded');
  response:=public.observation_call('get',jsonb_build_object('id',oid),worker);
  perform pg_temp.check_parameter(response->'current'->>'status'='invalidated','rejection status retained');

  key:=gen_random_uuid();
  input:=jsonb_build_object('idempotency_key',key,'measured_at','2020-01-02T00:15:00+05:30','fields',
   '{"original_label":"Weight","canonical_metric":"weight","raw_value":"70.250","numeric_value":"70.250","original_unit":"kg","value_kind":"numeric","comparator":null}'::jsonb);
  response:=public.observation_call('manual_create',input,worker); mid:=(response->>'id')::uuid;
  update pg_temp.parameter_test_context set candidate=oid,second=mid where label=actor.label;
  perform pg_temp.check_parameter(response->'current'->>'measurement_date' is null and (response->'current'->>'measured_at')::timestamptz=timestamptz '2020-01-01 18:45:00Z','manual offset preserved as instant');
  perform pg_temp.check_parameter(public.observation_call('manual_create',input,worker)->>'id'=mid::text,'manual replay');
  perform pg_temp.deny_parameter(format('select public.observation_call(''manual_create'',%L,%L)',jsonb_set(input,'{fields,original_unit}','"bpm"'),worker),'P0001');
  input:=input||jsonb_build_object('id',mid,'idempotency_key',gen_random_uuid(),'expected_revision',1);
  response:=public.observation_call('manual_edit',input,worker);
  perform pg_temp.check_parameter(jsonb_array_length(response->'revisions')=2,'manual audit revision');
  perform pg_temp.deny_parameter(format('select public.observation_call(''manual_edit'',%L,%L)',input||jsonb_build_object('idempotency_key',gen_random_uuid()),worker),'P0001');
  perform pg_temp.check_parameter(jsonb_array_length(public.observation_call('list','{"date_from":"2020-01-01","date_to":"2020-01-01"}',worker)->'items')=1,'UTC day boundary');
  perform pg_temp.check_parameter(jsonb_array_length(public.observation_call('list','{"date_from":"2020-01-02"}',worker)->'items')=0,'date filters exclude unknown');
  perform pg_temp.check_parameter((select count(*) from public.health_observations)=2,'owner RLS A/B');
  perform pg_temp.deny_parameter('insert into public.health_observations(user_id,source_type) values(gen_random_uuid(),''manual'')','42501');
  perform pg_temp.deny_parameter('update public.health_observation_revisions set status=''active''','42501');
  perform pg_temp.deny_parameter('delete from public.health_observations','42501');
  perform pg_temp.deny_parameter(format('select public.observation_call(''list'',''{}'',%L)',repeat('bad',20)),'42501');
  if other_actor.second is not null then
   perform pg_temp.deny_parameter(format('select public.observation_call(''get'',%L,%L)',jsonb_build_object('id',other_actor.second),worker),'P0001');
   perform pg_temp.deny_parameter(format('select public.observation_call(''manual_delete'',%L,%L)',jsonb_build_object('id',other_actor.second,'expected_revision',2),worker),'P0001');
  end if;
 end loop;
end; $$;
reset role;
-- Source deletion uses the existing Phase 4 deletion trigger and FK chain.
update public.reports set status='deleting' where id in(select report from parameter_test_context);
select pg_temp.check_parameter(not exists(select 1 from public.health_observations where source_type='report' and user_id in(select owner from parameter_test_context)),'physical report-derived cleanup');
select pg_temp.check_parameter((select count(*) from public.health_observations where source_type='manual' and user_id in(select owner from parameter_test_context))=2,'unrelated manual survives');
delete from auth.sessions where id=(select session from parameter_test_context where label='B');
set local role authenticated;
select set_config('request.jwt.claims',jsonb_build_object('sub',owner,'session_id',session,'role','authenticated','is_anonymous',false)::text,true) from parameter_test_context where label='B';
select pg_temp.check_parameter((select count(*) from public.health_observations)=0,'revoked RLS');
select pg_temp.deny_parameter(format('select public.observation_call(''list'',''{}'',%L)',repeat('synthetic',8)),'28000');
reset role;
select 'Phase 6 lifecycle assertions passed; fixtures roll back.' as result;
rollback;
