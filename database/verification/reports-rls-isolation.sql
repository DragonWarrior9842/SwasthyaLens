-- DEVELOPMENT ONLY: execute this complete ROLLBACK-only transaction.
-- Exercises actual database privileges/RLS/RPCs with random transaction fixtures.
-- It does not upload files, create Storage object metadata, or generate JWTs.
-- Successful binary upload/download/Storage policy acceptance needs the live suite.
begin;
set local statement_timeout = '30s';
set local lock_timeout = '5s';

create temporary table phase3_test_context (
  label text primary key,
  user_id uuid not null default gen_random_uuid(),
  session_id uuid not null default gen_random_uuid(),
  idempotency_key uuid not null default gen_random_uuid(),
  report_id uuid
) on commit drop;
insert into phase3_test_context(label) values ('A'), ('B');
grant select, update on phase3_test_context to authenticated;
grant select on phase3_test_context to anon;

insert into auth.users (id, aud, role, email, email_confirmed_at, created_at, updated_at)
select user_id, 'authenticated', 'authenticated', user_id::text || '@phase3-test.invalid',
  statement_timestamp(), statement_timestamp(), statement_timestamp()
from phase3_test_context;
insert into auth.sessions (id, user_id, created_at, updated_at)
select session_id, user_id, statement_timestamp() - interval '5 minutes', statement_timestamp()
from phase3_test_context;

create function pg_temp.phase3_assert(condition boolean, label text)
returns void language plpgsql security invoker as $$
begin
  if condition is distinct from true then raise exception 'FAILED: %', label; end if;
end;
$$;
create function pg_temp.phase3_expect_error(statement text, expected_state text,
  expected_message text, label text)
returns void language plpgsql security invoker as $$
begin
  begin
    execute statement;
  exception when others then
    if sqlstate = expected_state
      and (expected_message is null or sqlerrm = expected_message) then return; end if;
    raise exception 'FAILED: %, expected SQLSTATE %, got %', label, expected_state, sqlstate;
  end;
  raise exception 'FAILED: %, statement unexpectedly succeeded', label;
end;
$$;

set local role authenticated;
do $$
declare actor record; document jsonb; duplicate_document jsonb;
begin
  for actor in select * from pg_temp.phase3_test_context order by label loop
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    document := public.report_reserve('fixture.pdf', 'application/pdf', 128,
      actor.idempotency_key);
    update pg_temp.phase3_test_context set report_id = (document ->> 'id')::uuid
      where label = actor.label;
    perform pg_temp.phase3_assert(document ->> 'user_id' = actor.user_id::text,
      actor.label || ' authoritative owner');
    perform pg_temp.phase3_assert(document ->> 'status' = 'pending_upload',
      actor.label || ' truthful initial status');
    perform pg_temp.phase3_assert(document ->> 'storage_path' like
      actor.user_id::text || '/' || (document ->> 'id') || '/%',
      actor.label || ' generated ownership path');
    duplicate_document := public.report_reserve('fixture.pdf', 'application/pdf', 128,
      actor.idempotency_key);
    perform pg_temp.phase3_assert(duplicate_document ->> 'id' = document ->> 'id',
      actor.label || ' idempotent reservation');
    perform pg_temp.phase3_expect_error(format(
      'select public.report_reserve(''different.pdf'',''application/pdf'',128,%L)',
      actor.idempotency_key), 'P0001', 'report_conflict', actor.label || ' dedupe conflict');
    perform pg_temp.phase3_expect_error(
      'select public.report_reserve(''../bad.pdf'',''application/pdf'',128,gen_random_uuid())',
      'P0001', 'invalid_file', actor.label || ' traversal filename');
    perform pg_temp.phase3_expect_error(
      'select public.report_reserve(''bad.svg'',''image/svg+xml'',128,gen_random_uuid())',
      'P0001', 'invalid_file', actor.label || ' unsupported file');
    perform pg_temp.phase3_expect_error(
      'select public.report_reserve(''empty.pdf'',''application/pdf'',0,gen_random_uuid())',
      'P0001', 'invalid_file', actor.label || ' empty file');
    perform pg_temp.phase3_expect_error(
      'select public.report_reserve(''big.pdf'',''application/pdf'',5242881,gen_random_uuid())',
      'P0001', 'invalid_file', actor.label || ' database size cap');
  end loop;
end;
$$;

do $$
declare actor record; other_report uuid; other_owner uuid; document jsonb; lease uuid;
begin
  for actor in select * from pg_temp.phase3_test_context order by label loop
    select report_id, user_id into other_report, other_owner
      from pg_temp.phase3_test_context where label <> actor.label;
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    perform pg_temp.phase3_assert((select count(*) from public.reports) = 1,
      actor.label || ' unfiltered SELECT isolates owner');
    perform pg_temp.phase3_assert((select count(*) from public.reports where id = other_report) = 0,
      actor.label || ' other owner report hidden');
    perform pg_temp.phase3_expect_error(format(
      'insert into public.reports(user_id,idempotency_key) values(%L,gen_random_uuid())',
      other_owner), '42501', null, actor.label || ' direct forged INSERT forbidden');
    perform pg_temp.phase3_expect_error(format(
      'update public.reports set user_id=%L where id=%L', other_owner, actor.report_id),
      '42501', null, actor.label || ' direct owner UPDATE forbidden');
    perform pg_temp.phase3_expect_error('update public.reports set status=''uploaded''',
      '42501', null, actor.label || ' fake completion forbidden');
    perform pg_temp.phase3_expect_error('delete from public.reports',
      '42501', null, actor.label || ' hard DELETE forbidden');
    perform pg_temp.phase3_expect_error(format('select public.report_begin_delete(%L)', other_report),
      'P0001', 'report_not_found', actor.label || ' cross-user lifecycle hidden');
    perform pg_temp.phase3_expect_error(format(
      'select public.report_begin_upload(%L,%L)', other_report, repeat('a', 64)),
      'P0001', 'report_not_found', actor.label || ' cross-user upload hidden');
    document := public.report_begin_upload(actor.report_id, repeat('a', 64));
    lease := (document ->> 'lease_token')::uuid;
    perform pg_temp.phase3_assert(document ->> 'status' = 'uploading'
      and lease is not null and (document ->> 'upload_lease_expires_at')::timestamptz
        > statement_timestamp(), actor.label || ' exclusive upload lease');
    perform pg_temp.phase3_expect_error(format(
      'select public.report_begin_upload(%L,%L)', actor.report_id, repeat('a', 64)),
      'P0001', 'report_conflict', actor.label || ' concurrent upload denied');
    perform pg_temp.phase3_expect_error(format(
      'select public.report_finish_upload(%L,%L)', actor.report_id, lease),
      'P0001', 'report_conflict', actor.label || ' cannot finish without actual Storage object');
    document := public.report_fail_upload(actor.report_id, lease, 'storage_unavailable');
    perform pg_temp.phase3_assert(document ->> 'status' = 'upload_failed'
      and document ->> 'lease_token' = lease::text
      and document ->> 'sha256' = repeat('a', 64), actor.label || ' uncertain upload remains tracked');
    document := public.report_begin_delete(actor.report_id);
    perform pg_temp.phase3_assert(document ->> 'status' = 'deleting'
      and document ->> 'lease_token' = lease::text, actor.label || ' cancellation retains lease');
    perform pg_temp.phase3_expect_error(format('select public.report_finish_delete(%L)', actor.report_id),
      'P0001', 'report_conflict', actor.label || ' deletion waits for possible in-flight upload');
    document := public.report_fail_upload(actor.report_id, lease, 'storage_unavailable');
    perform pg_temp.phase3_assert(document ->> 'status' = 'deleting',
      actor.label || ' late failure cannot reverse cancellation');
  end loop;
end;
$$;

-- Advance only these transaction fixture leases; no real account/report is touched.
reset role;
update public.reports set upload_lease_expires_at = statement_timestamp() - interval '1 second'
where id in (select report_id from pg_temp.phase3_test_context);
set local role authenticated;
do $$
declare actor record; document jsonb; candidates jsonb;
begin
  for actor in select * from pg_temp.phase3_test_context order by label loop
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    candidates := public.report_cleanup_candidates(10);
    perform pg_temp.phase3_assert(jsonb_array_length(candidates) = 1
      and candidates -> 0 ->> 'user_id' = actor.user_id::text,
      actor.label || ' cleanup candidates isolated');
    document := public.report_finish_delete(actor.report_id);
    perform pg_temp.phase3_assert(document ->> 'status' = 'deleted'
      and document ->> 'original_filename' is null and document ->> 'media_type' is null
      and document ->> 'size_bytes' is null and document ->> 'sha256' is null
      and document ->> 'lease_token' is null and document ->> 'storage_path' is not null,
      actor.label || ' deleted tombstone scrubs file metadata and retains cleanup path');
    document := public.report_begin_delete(actor.report_id);
    perform pg_temp.phase3_assert(document ->> 'status' = 'deleted',
      actor.label || ' retry delete stays deleted');
    perform public.report_touch_cleanup(actor.report_id);
    perform pg_temp.phase3_expect_error(format(
      'select public.report_reserve(''fixture.pdf'',''application/pdf'',128,%L)',
      actor.idempotency_key), 'P0001', 'report_conflict', actor.label || ' tombstone prevents resurrection');
  end loop;
end;
$$;

reset role;
do $$
declare actor record;
begin
  for actor in select * from pg_temp.phase3_test_context loop
    perform pg_temp.phase3_expect_error(format('delete from auth.users where id=%L', actor.user_id),
      '23503', null, actor.label || ' account deletion cannot discard cleanup manifest');
  end loop;
end;
$$;
delete from auth.sessions where id in (select session_id from pg_temp.phase3_test_context);
set local role authenticated;
do $$
declare actor record;
begin
  for actor in select * from pg_temp.phase3_test_context loop
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    perform pg_temp.phase3_assert((select count(*) from public.reports) = 0,
      actor.label || ' revoked session cannot read reports');
    perform pg_temp.phase3_expect_error(format('select public.report_begin_delete(%L)', actor.report_id),
      '28000', 'report_session_inactive', actor.label || ' revoked session cannot mutate reports');
  end loop;
end;
$$;
reset role;
set local role anon;
select pg_temp.phase3_expect_error('select * from public.reports',
  '42501', null, 'anonymous report reads denied');
select pg_temp.phase3_expect_error(
  'select public.report_reserve(''fixture.pdf'',''application/pdf'',128,gen_random_uuid())',
  '42501', null, 'anonymous report reservation denied');
reset role;

select 'Phase 3 database isolation/lifecycle assertions passed; fixtures roll back next.' as result;
rollback;
