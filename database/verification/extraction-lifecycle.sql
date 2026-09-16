-- Development-only rollback test. No Storage objects are created or modified.
begin;
set local statement_timeout='30s';
set local lock_timeout='5s';
create temporary table extraction_test_context(label text primary key, owner uuid default gen_random_uuid(),
  session uuid default gen_random_uuid(), report uuid default gen_random_uuid(), run uuid, second uuid) on commit drop;
insert into extraction_test_context(label) values('A'),('B');
grant select,update on extraction_test_context to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
select owner,'authenticated','authenticated',owner::text||'@phase4.invalid',now(),now(),now() from extraction_test_context;
insert into auth.sessions(id,user_id,created_at,updated_at)
select session,owner,now()-interval '5 minutes',now() from extraction_test_context;
insert into public.reports(id,user_id,idempotency_key,storage_path,original_filename,media_type,size_bytes,sha256,status)
select report,owner,gen_random_uuid(),owner::text||'/'||report::text||'/'||gen_random_uuid()::text||'.pdf',
  'synthetic.pdf','application/pdf',100,repeat('a',64),'uploaded' from extraction_test_context;
update swasthyalens_private.processing_key set sha256=encode(extensions.digest(repeat('synthetic',8),'sha256'),'hex');

create function pg_temp.assert_extraction(ok boolean, label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
create function pg_temp.expect_extraction_error(statement text, expected text) returns void language plpgsql as $$
begin
  begin execute statement;
  exception when others then
    if sqlstate=expected then return; end if;
    raise exception 'Unexpected SQLSTATE %, expected %',sqlstate,expected;
  end;
  raise exception 'Expected denial did not occur';
end; $$;

set local role authenticated;
do $$
declare actor record; other_report uuid; result jsonb; duplicate jsonb;
  key uuid; worker text := repeat('synthetic',8);
  payload jsonb := '{"processor":"synthetic-sql-fixture","configuration":{},"pages":[{"page_number":1,"method":"native_text","text":"Synthetic source only"}]}'::jsonb;
begin
  for actor in select * from pg_temp.extraction_test_context order by label loop
    perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
    key := gen_random_uuid();
    result := public.processing_request_configured(actor.report,key,worker,'planned-test-engine','{"max_pages":20}');
    perform pg_temp.assert_extraction(result->>'processor'='planned-test-engine','queued processor retained');
    duplicate := public.processing_request(actor.report,gen_random_uuid(),worker);
    perform pg_temp.assert_extraction(result->>'id'=duplicate->>'id','active request deduplication');
    update pg_temp.extraction_test_context set run=(result->>'id')::uuid where label=actor.label;
    perform pg_temp.assert_extraction(public.processing_start(actor.report,(result->>'id')::uuid,worker),'first claim');
    perform pg_temp.assert_extraction(not public.processing_start(actor.report,(result->>'id')::uuid,worker),'second claim denied');
    perform pg_temp.assert_extraction(public.processing_finish(actor.report,(result->>'id')::uuid,payload,null,worker),'success committed');
    perform pg_temp.assert_extraction(not public.processing_finish(actor.report,(result->>'id')::uuid,payload,null,worker),'successful machine output immutable');
    perform pg_temp.assert_extraction((select count(*) from public.report_pages)=1,'owner-only pages');
    select report into other_report from pg_temp.extraction_test_context where label<>actor.label;
    perform pg_temp.expect_extraction_error(format('select public.processing_request(%L,gen_random_uuid(),%L)',other_report,worker),'P0001');
    perform pg_temp.expect_extraction_error(format('select public.processing_start(%L,gen_random_uuid(),%L)',other_report,worker),'P0001');
    perform pg_temp.expect_extraction_error(format('select public.processing_finish(%L,gen_random_uuid(),null,''timeout'',%L)',other_report,worker),'P0001');
    perform pg_temp.expect_extraction_error(format('select public.processing_request(%L,gen_random_uuid(),''forged'')',actor.report),'42501');
    perform pg_temp.expect_extraction_error('delete from public.report_pages','42501');
    perform pg_temp.expect_extraction_error('update public.report_processing_runs set status=''completed''','42501');
    result := public.processing_request_configured(actor.report,gen_random_uuid(),worker,'retry-test-engine','{"max_pages":10}');
    update pg_temp.extraction_test_context set second=(result->>'id')::uuid where label=actor.label;
    perform pg_temp.assert_extraction(public.processing_start(actor.report,(result->>'id')::uuid,worker),'retry claim');
  end loop;
end; $$;

reset role;
-- Simulate loss of both workers beyond their durable deadline.
update public.report_processing_runs set deadline_at=now()-interval '1 second'
where id in (select second from extraction_test_context);
set local role authenticated;
do $$
declare actor record; history jsonb; third jsonb; worker text := repeat('synthetic',8);
begin
  for actor in select * from pg_temp.extraction_test_context order by label loop
    perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
    history := public.processing_history(actor.report,worker);
    perform pg_temp.assert_extraction(history->0->>'status'='failed' and history->0->>'error_category'='interrupted','expired worker recovered');
    perform pg_temp.assert_extraction(history->0->>'processor'='retry-test-engine' and history->0->'configuration'->>'max_pages'='10','interrupted configuration retained');
    perform pg_temp.assert_extraction(history->1->>'status'='completed','previous success retained');
    perform pg_temp.assert_extraction((select count(*) from public.report_pages)=1,'previous successful text retained');
    perform pg_temp.assert_extraction(not public.processing_finish(actor.report,actor.second,null,'timeout',worker),'late worker fenced');
    third := public.processing_request(actor.report,gen_random_uuid(),worker);
    perform pg_temp.assert_extraction(third->>'attempt'='3','bounded retry recorded');
    if actor.label='A' then
      perform public.report_begin_delete(actor.report);
      perform pg_temp.assert_extraction((select count(*) from public.report_pages)=0,'deletion hides derived text');
      perform pg_temp.expect_extraction_error(format('select public.processing_start(%L,%L,%L)',actor.report,third->>'id',worker),'P0001');
    end if;
  end loop;
end; $$;
reset role;
do $$ begin
  perform pg_temp.assert_extraction(not exists(select 1 from public.report_processing_runs where report_id=(select report from extraction_test_context where label='A')),'deletion physically erases runs/pages via cascade');
end; $$;
-- B's source and successful text still exist when its session is revoked.
delete from auth.sessions where id=(select session from extraction_test_context where label='B');
set local role authenticated;
do $$ declare actor record; begin
  select * into actor from pg_temp.extraction_test_context where label='B';
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
  perform pg_temp.assert_extraction((select count(*) from public.report_pages)=0,'revoked session cannot read existing pages');
  perform pg_temp.expect_extraction_error(format('select public.processing_request(%L,gen_random_uuid(),%L)',actor.report,repeat('synthetic',8)),'28000');
end; $$;
reset role;
rollback;
