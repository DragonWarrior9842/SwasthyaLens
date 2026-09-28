-- Synthetic identities only; run the complete transaction and always roll back.
begin;
set local statement_timeout='30s';
set local lock_timeout='5s';
create temporary table phase11_context(label text primary key,owner uuid default gen_random_uuid(),
 session uuid default gen_random_uuid(),report uuid default gen_random_uuid(),source uuid default gen_random_uuid(),
 notice uuid,manual uuid,observation uuid,candidate uuid) on commit drop;
insert into phase11_context(label) values('A'),('B');
grant select,update on phase11_context to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
 select owner,'authenticated','authenticated',owner::text||'@phase11.invalid',now(),now(),now() from phase11_context;
insert into auth.sessions(id,user_id,created_at,updated_at)
 select session,owner,now()-interval '5 minutes',now() from phase11_context;
insert into public.user_settings(user_id) select owner from phase11_context;
insert into public.reports(id,user_id,idempotency_key,storage_path,original_filename,media_type,size_bytes,status)
 select report,owner,gen_random_uuid(),owner::text||'/'||report::text||'/'||gen_random_uuid()::text||'.pdf',
 'synthetic-phase11.pdf','application/pdf',100,'pending_upload' from phase11_context;
create function pg_temp.verify(ok boolean,label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
create function pg_temp.denied(statement text,expected text) returns void language plpgsql as $$
begin begin execute statement; exception when others then if sqlstate=expected then return; end if;
raise exception 'Unexpected SQLSTATE %, expected %',sqlstate,expected; end; raise exception 'Expected denial did not occur'; end; $$;
select pg_temp.verify((select count(*)=0 from public.notifications where user_id in(select owner from phase11_context)),'no notification for pending upload');
update public.reports set status='uploaded',sha256=repeat('a',64) where id in(select report from phase11_context);
update public.reports set status='uploaded' where id in(select report from phase11_context);
select pg_temp.verify((select count(*)=2 from public.notifications where user_id in(select owner from phase11_context)),'upload transition once per owner');
insert into public.report_processing_runs(id,report_id,idempotency_key,source_sha256,attempt,status)
 select source,report,gen_random_uuid(),repeat('a',64),1,'queued' from phase11_context;
select pg_temp.verify((select count(*)=2 from public.notifications where user_id in(select owner from phase11_context)),'no success at processing start');
update public.report_processing_runs set status='completed',finished_at=now(),processor='synthetic',page_count=1
 where id in(select source from phase11_context);
insert into public.report_pages(run_id,page_number,content)
 select source,1,'{"text":"Test | Result\nSynthetic | 5","method":"native_text"}' from phase11_context;
update swasthyalens_private.processing_key set sha256=encode(extensions.digest(repeat('synthetic',8),'sha256'),'hex');
set local role authenticated;
do $$
declare actor record; other_actor record; payload jsonb; result jsonb; old_read text; identifier uuid; candidate uuid;
 worker text:=repeat('synthetic',8); report_observation uuid;
begin
 for actor in select * from pg_temp.phase11_context order by label loop
  select * into other_actor from pg_temp.phase11_context where label<>actor.label;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
  perform pg_temp.verify((select count(*)=2 from public.notifications),'owner notifications only');
  perform pg_temp.verify((select count(*)=0 from public.notifications where user_id=other_actor.owner),'foreign notifications hidden');
  perform pg_temp.denied('insert into public.notifications(user_id,report_id,event_type,event_key) values(gen_random_uuid(),gen_random_uuid(),''upload_completed'',gen_random_uuid())','42501');
  perform pg_temp.denied('update public.notifications set read_at=now()','42501');
  perform pg_temp.denied('delete from public.notifications','42501');
  result:=public.notification_call('list',null,0,worker);
  perform pg_temp.verify((result->>'unread_count')::integer=2,'truthful unread count');
  identifier:=(result->'items'->0->>'id')::uuid;
  perform public.notification_call('read',identifier,0,worker);
  select read_at::text into old_read from public.notifications where id=identifier;
  perform public.notification_call('read',identifier,0,worker);
  perform pg_temp.verify((select read_at::text=old_read from public.notifications where id=identifier),'read replay preserves timestamp');
  update pg_temp.phase11_context set notice=identifier where label=actor.label;
  perform pg_temp.verify((public.notification_call('read_all',null,0,worker)->>'unread_count')::integer=0,'mark all owned read');
  perform pg_temp.denied(format('select public.notification_call(''list'',null,0,%L)',repeat('bad',20)),'42501');
  perform pg_temp.denied(format('select public.export_context(''2020-01-01'',''2021-01-01'',true,null,null)'),'P0001');
  perform pg_temp.denied(format('select public.export_context(''2020-01-01'',''2020-12-31'',true,null,%L)',other_actor.report),'P0001');
  result:=public.observation_call('manual_create',jsonb_build_object('idempotency_key',gen_random_uuid(),
   'measured_at','2020-01-02T00:15:00+05:30','fields','{"original_label":"Weight","canonical_metric":"weight","raw_value":"13.20","numeric_value":"13.20","original_unit":"kg","value_kind":"numeric"}'::jsonb),worker);
  update pg_temp.phase11_context set manual=(result->>'id')::uuid where label=actor.label;
  result:=public.parameter_request(actor.report,actor.source,gen_random_uuid(),'v1','v1',worker);
  payload:='[{"page_number":1,"source_text":"Synthetic | 5","source_start":14,"source_end":27,"source_method":"native_text","certainty":"needs_review","fields":{"original_label":"Synthetic","raw_value":"<5","original_unit":"mg/dL","raw_reference":"30–100","value_kind":"numeric","numeric_value":"5","comparator":"<"}}]';
  perform public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker);
  perform public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker);
  perform pg_temp.verify((select count(*)=1 from public.notifications where event_type='parameters_ready'),'one real review-ready notification');
  select id into candidate from public.report_parameter_candidates where run_id=(result->'run'->>'id')::uuid;
  result:=public.export_context('2020-01-01','2020-12-31',true,null,null);
  perform pg_temp.verify(jsonb_array_length(result->'items')=1,'unreviewed candidates excluded');
  perform public.parameter_review(actor.report,candidate,gen_random_uuid(),0,'confirmed',null,worker);
  perform pg_temp.verify(jsonb_array_length(public.export_context('2020-01-01','2020-12-31',true,null,null)->'items')=1,'review alone excluded');
  result:=public.observation_call('publish',jsonb_build_object('report_id',actor.report,'candidate_id',candidate,'expected_revision',1),worker);
  report_observation:=(result->>'id')::uuid;
  update pg_temp.phase11_context set observation=report_observation where label=actor.label;
  result:=public.export_context('2020-01-01','2020-01-01',true,null,null);
  perform pg_temp.verify(jsonb_array_length(result->'items')=2,'published plus UTC manual day');
  perform pg_temp.verify((select count(*)=2 from jsonb_array_elements(result->'items') x where x->>'user_id'=actor.owner::text),'all export rows owned');
  perform pg_temp.verify(jsonb_array_length(public.export_context('2020-01-01','2020-01-01',false,null,null)->'items')=1,'unknown date opt-in');
  perform public.parameter_review(actor.report,candidate,gen_random_uuid(),1,'rejected',null,worker);
  perform pg_temp.verify(jsonb_array_length(public.export_context('2020-01-01','2020-12-31',true,null,null)->'items')=1,'correction excludes stale publication');
 end loop;
end; $$;
-- Privileged fixture modifications target only the newly created owners.
reset role;
update public.notifications set created_at=now()-interval '31 days' where id=(select notice from phase11_context where label='A');
set local role authenticated;
do $$
declare a record; b record; worker text:=repeat('synthetic',8);
begin
 select * into a from pg_temp.phase11_context where label='A'; select * into b from pg_temp.phase11_context where label='B';
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a.owner,'session_id',a.session,'role','authenticated','is_anonymous',false)::text,true);
 perform pg_temp.verify(not exists(select 1 from public.notifications where id=a.notice),'expired row hidden by RLS');
 perform pg_temp.denied(format('select public.notification_call(''read'',%L,0,%L)',a.notice,worker),'P0001');
 perform pg_temp.denied(format('select public.notification_call(''read'',%L,0,%L)',b.notice,worker),'P0001');
 perform pg_temp.denied(format('select public.notification_call(''delete'',%L,0,%L)',b.notice,worker),'P0001');
 perform public.report_begin_delete(a.report);
 perform pg_temp.verify((select count(*)=0 from public.notifications),'report deletion clears notices');
 perform pg_temp.verify(jsonb_array_length(public.export_context('2020-01-01','2020-12-31',true,null,null)->'items')=1,'deleted report excluded and unrelated manual retained');
 perform public.observation_call('manual_delete',jsonb_build_object('id',a.manual,'expected_revision',1),worker);
 perform pg_temp.verify(jsonb_array_length(public.export_context('2020-01-01','2020-12-31',true,null,null)->'items')=0,'manual deletion absent on regeneration');
end; $$;
reset role;
delete from auth.sessions where id in(select session from phase11_context);
set local role authenticated;
select pg_temp.verify((select count(*)=0 from public.notifications),'revoked session hides notices');
select pg_temp.denied('select public.export_context(''2020-01-01'',''2020-12-31'',true,null,null)','28000');
rollback;
