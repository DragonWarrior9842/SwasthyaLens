-- Retention/capacity and real failed/empty transitions, synthetic rollback fixtures.
begin;
set local statement_timeout='30s';
create temporary table p11_limits(owner uuid default gen_random_uuid(),session uuid default gen_random_uuid(),
 report uuid default gen_random_uuid(),run uuid default gen_random_uuid()) on commit drop;
insert into p11_limits default values;
grant select on p11_limits to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
 select owner,'authenticated','authenticated',owner::text||'@p11limits.invalid',now(),now(),now() from p11_limits;
insert into auth.sessions(id,user_id,created_at,updated_at) select session,owner,now()-interval '1 minute',now() from p11_limits;
insert into public.user_settings(user_id,in_app_notifications) select owner,false from p11_limits;
insert into public.reports(id,user_id,idempotency_key,storage_path,original_filename,media_type,size_bytes,status)
 select report,owner,gen_random_uuid(),owner::text||'/'||report::text||'/'||gen_random_uuid()::text||'.pdf',
 'synthetic.pdf','application/pdf',100,'pending_upload' from p11_limits;
update public.reports set status='uploaded',sha256=repeat('a',64) where id=(select report from p11_limits);
create function pg_temp.check_limit(ok boolean,label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
select pg_temp.check_limit((select count(*)=0 from public.notifications where user_id=(select owner from p11_limits)),'disabled notifications suppress future events');
update public.user_settings set in_app_notifications=true where user_id=(select owner from p11_limits);
insert into public.notifications(user_id,report_id,event_type,event_key,created_at)
 select owner,report,'upload_completed',gen_random_uuid(),now()-interval '1 day' from p11_limits,generate_series(1,101);
insert into public.report_processing_runs(id,report_id,idempotency_key,source_sha256,attempt,status)
 select run,report,gen_random_uuid(),repeat('a',64),1,'queued' from p11_limits;
update public.report_processing_runs set status='failed',error_category='interrupted',finished_at=now() where id=(select run from p11_limits);
select pg_temp.check_limit((select count(*)=100 from public.notifications where user_id=(select owner from p11_limits)),'cap retains 100 newest');
select pg_temp.check_limit((select count(*)=1 from public.notifications where report_id=(select report from p11_limits) and event_type='extraction_failed'),'failure emits truthful event');
update public.report_processing_runs set status='failed' where id=(select run from p11_limits);
select pg_temp.check_limit((select count(*)=1 from public.notifications where report_id=(select report from p11_limits) and event_type='extraction_failed'),'failure replay does not duplicate');
update public.notifications set created_at=now()-interval '31 days' where user_id=(select owner from p11_limits);
select swasthyalens_private.notification_cleanup();
select pg_temp.check_limit((select count(*)=0 from public.notifications where user_id=(select owner from p11_limits)),'scheduled cleanup removes expired notices');
-- A completed source permits parameter transitions without real provider/OCR I/O.
insert into public.report_processing_runs(report_id,idempotency_key,source_sha256,attempt,status,finished_at,processor,page_count)
 select report,gen_random_uuid(),repeat('a',64),2,'completed',now(),'synthetic',1 from p11_limits;
insert into public.report_parameter_runs(report_id,source_run_id,idempotency_key,attempt,status,extractor_version,rules_version)
 select report_id,id,gen_random_uuid(),1,'processing','v1','v1' from public.report_processing_runs where report_id=(select report from p11_limits) and attempt=2;
update public.report_parameter_runs set status='completed',finished_at=now(),candidate_count=0 where report_id=(select report from p11_limits);
select pg_temp.check_limit((select count(*)=0 from public.notifications where user_id=(select owner from p11_limits)),'empty candidates do not claim review required');
insert into public.report_parameter_runs(report_id,source_run_id,idempotency_key,attempt,status,extractor_version,rules_version)
 select report_id,source_run_id,gen_random_uuid(),2,'processing','v1','v1' from public.report_parameter_runs where report_id=(select report from p11_limits);
update public.report_parameter_runs set status='failed',finished_at=now(),error_category='parser_failure' where report_id=(select report from p11_limits) and status='processing';
select pg_temp.check_limit((select count(*)=1 from public.notifications where user_id=(select owner from p11_limits) and event_type='parameters_failed'),'parameter failure has its own operational event');
insert into public.health_observations(user_id,source_type,idempotency_key)
 select owner,'manual',gen_random_uuid() from p11_limits,generate_series(1,201);
insert into public.health_observation_revisions(observation_id,revision,status,fields,measured_at,idempotency_key)
 select id,1,'active','{"original_label":"Weight","raw_value":"13.20","original_unit":"kg","value_kind":"numeric"}',
 '2020-01-01T00:00:00Z',gen_random_uuid() from public.health_observations where user_id=(select owner from p11_limits);
set local role authenticated;
do $$
declare fixture record;
begin
 select * into fixture from pg_temp.p11_limits;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',fixture.owner,'session_id',fixture.session,'role','authenticated','is_anonymous',false)::text,true);
 begin perform public.export_context('2020-01-01','2020-12-31',false,null,null);
 exception when sqlstate 'P0001' then
  if sqlerrm='export_capacity' then return; end if; raise;
 end;
 raise exception 'Oversized export was not rejected';
end; $$;
rollback;
