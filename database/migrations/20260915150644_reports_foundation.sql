-- SwasthyaLens Phase 3. Apply once after auth_foundation.
-- Bucket creation is the documented SQL setup exception; all object mutations
-- use the Storage API. No provider-owned schema structure or object rows change.
begin;

do $$
begin
  if to_regprocedure('storage.allow_any_operation(text[])') is null
    or to_regprocedure('storage.allow_only_operation(text)') is null
    or to_regprocedure('swasthyalens_private.session_is_active()') is null then
    raise exception 'Required session/Storage policy helpers are unavailable';
  end if;
  if exists (select 1 from storage.buckets where id = 'reports' or name = 'reports') then
    raise exception 'Unexpected existing reports bucket; review configuration before applying';
  end if;
  if exists (select 1 from pg_catalog.pg_policies
      where schemaname = 'storage' and tablename = 'objects') then
    raise exception 'Unexpected existing Storage policies; review permissive policy overlap before applying';
  end if;
end;
$$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('reports', 'reports', false, 5242880,
  array['application/pdf', 'image/jpeg', 'image/png']::text[]);

create function swasthyalens_private.report_metadata_valid(
  p_filename text, p_media_type text, p_size_bytes bigint)
returns boolean language sql immutable security invoker set search_path = '' as $$
  select coalesce(
    p_filename = btrim(p_filename)
    and char_length(p_filename) between 1 and 120
    and octet_length(p_filename) <= 240
    and p_filename is NFC normalized
    and p_filename !~ '[[:cntrl:]/\\:*?"<>|]'
    -- Explicit Unicode format controls are not consistently classified by
    -- database locales. Reject bidi overrides/isolates, invisible separators,
    -- BOM, interlinear annotation and tag controls at the direct RPC boundary.
    and p_filename !~ U&'[\00AD\061C\180E\200B-\200F\2028-\202E\2060-\206F\FEFF\FFF9-\FFFB\+0E0001\+0E0020-\+0E007F]'
    and p_filename !~ '^\.' and p_filename !~ '\.$'
    and position('..' in p_filename) = 0
    and p_filename !~* '^(con|prn|aux|nul|com[1-9]|lpt[1-9])([.]|$)'
    and p_size_bytes between 1 and 5242880
    and ((p_media_type = 'application/pdf' and p_filename ~* '[.]pdf$')
      or (p_media_type = 'image/jpeg' and p_filename ~* '[.]jpe?g$')
      or (p_media_type = 'image/png' and p_filename ~* '[.]png$')), false);
$$;

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete restrict,
  idempotency_key uuid not null,
  storage_path text not null unique,
  original_filename text,
  media_type text,
  size_bytes bigint,
  sha256 text,
  status text not null default 'pending_upload',
  lease_token uuid,
  upload_lease_expires_at timestamptz,
  error_category text,
  created_at timestamptz not null default statement_timestamp(),
  updated_at timestamptz not null default statement_timestamp(),
  deleted_at timestamptz,
  cleanup_checked_at timestamptz,
  constraint reports_owner_idempotency_key unique (user_id, idempotency_key),
  constraint reports_status_valid check (status in
    ('pending_upload', 'uploading', 'uploaded', 'upload_failed', 'deleting', 'deleted')),
  constraint reports_path_valid check (
    storage_path ~ ('^' || user_id::text || '/' || id::text
      || '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[.](pdf|jpg|png)$')),
  constraint reports_metadata_valid check (
    (status <> 'deleted' and deleted_at is null
      and swasthyalens_private.report_metadata_valid(original_filename, media_type, size_bytes))
    or (status = 'deleted' and deleted_at is not null and original_filename is null
      and media_type is null and size_bytes is null and sha256 is null
      and lease_token is null and upload_lease_expires_at is null and error_category is null)),
  constraint reports_digest_valid check (sha256 is null or sha256 ~ '^[0-9a-f]{64}$'),
  constraint reports_lease_pair check (
    (lease_token is null) = (upload_lease_expires_at is null)),
  constraint reports_upload_lease_required check (
    status <> 'uploading' or (lease_token is not null and sha256 is not null)),
  constraint reports_uploaded_valid check (
    status <> 'uploaded' or (sha256 is not null and lease_token is null)),
  constraint reports_pending_valid check (
    status <> 'pending_upload' or (sha256 is null and lease_token is null)),
  constraint reports_error_category_valid check (error_category is null or error_category in
    ('invalid_file', 'file_too_large', 'unsupported_file_type', 'filename_invalid',
      'storage_unavailable', 'metadata_unavailable', 'upload_interrupted', 'integrity_mismatch'))
);

create index reports_owner_history_idx on public.reports(user_id, created_at desc, id desc)
  where status <> 'deleted';
create index reports_cleanup_idx
  on public.reports(user_id, cleanup_checked_at asc nulls first, created_at, id)
  where status in ('deleting', 'deleted');
create trigger reports_set_updated_at before update on public.reports
for each row execute function swasthyalens_private.set_updated_at();

alter table public.reports enable row level security;
alter table public.reports force row level security;
revoke all on table public.reports from public, anon, authenticated, service_role;
grant select on table public.reports to authenticated;

-- Runtime mutations have no table grants. These policies retain ownership
-- defense if a later reviewed migration adds restricted column privileges.
create policy reports_select_own_active on public.reports for select to authenticated
  using (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy reports_insert_own_active on public.reports for insert to authenticated
  with check (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy reports_update_own_active on public.reports for update to authenticated
  using (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()))
  with check (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy reports_delete_own_active on public.reports for delete to authenticated
  using (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));

create function swasthyalens_private.report_require_user()
returns uuid language plpgsql stable security invoker set search_path = '' as $$
begin
  if not swasthyalens_private.session_is_active() then
    raise exception using errcode = '28000', message = 'report_session_inactive';
  end if;
  return auth.uid();
end;
$$;

-- Narrow private definers protect lifecycle/immutable columns from direct REST
-- writes. Every entry point checks the verified JWT's active session and owner.
-- No function accepts an authoritative owner ID or performs a global mutation.
create function swasthyalens_private.report_reserve(
  p_filename text, p_media_type text, p_size_bytes bigint, p_idempotency_key uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  caller uuid := swasthyalens_private.report_require_user();
  report_id uuid := gen_random_uuid();
  object_id uuid := gen_random_uuid();
  extension text;
  document public.reports%rowtype;
begin
  if p_idempotency_key is null or p_idempotency_key = '00000000-0000-0000-0000-000000000000'::uuid
    or not swasthyalens_private.report_metadata_valid(p_filename, p_media_type, p_size_bytes) then
    raise exception using errcode = 'P0001', message = 'invalid_file';
  end if;
  extension := case p_media_type when 'application/pdf' then 'pdf'
    when 'image/jpeg' then 'jpg' else 'png' end;
  insert into public.reports(user_id, id, idempotency_key, storage_path,
    original_filename, media_type, size_bytes)
  values (caller, report_id, p_idempotency_key,
    caller::text || '/' || report_id::text || '/' || object_id::text || '.' || extension,
    p_filename, p_media_type, p_size_bytes)
  on conflict (user_id, idempotency_key) do nothing
  returning * into document;
  if not found then
    select * into document from public.reports
      where user_id = caller and idempotency_key = p_idempotency_key for update;
    if not found or document.status in ('deleting', 'deleted')
      or document.original_filename is distinct from p_filename
      or document.media_type is distinct from p_media_type
      or document.size_bytes is distinct from p_size_bytes then
      raise exception using errcode = 'P0001', message = 'report_conflict';
    end if;
  end if;
  return to_jsonb(document);
end;
$$;

create function swasthyalens_private.report_begin_upload(p_report_id uuid, p_sha256 text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  caller uuid := swasthyalens_private.report_require_user();
  document public.reports%rowtype;
begin
  select * into document from public.reports
    where id = p_report_id and user_id = caller for update;
  if not found then raise exception using errcode = 'P0001', message = 'report_not_found'; end if;
  if p_sha256 is null or p_sha256 !~ '^[0-9a-f]{64}$' then
    raise exception using errcode = 'P0001', message = 'invalid_file';
  end if;
  if document.sha256 is not null and document.sha256 <> p_sha256 then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  if document.status = 'uploaded' then return to_jsonb(document); end if;
  if document.status not in ('pending_upload', 'upload_failed', 'uploading')
    or document.upload_lease_expires_at > statement_timestamp() then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  update public.reports set status = 'uploading', sha256 = p_sha256,
    lease_token = gen_random_uuid(), upload_lease_expires_at = statement_timestamp() + interval '120 seconds',
    error_category = null
  where id = document.id and user_id = caller returning * into document;
  return to_jsonb(document);
end;
$$;

create function swasthyalens_private.report_finish_upload(p_report_id uuid, p_lease_token uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  caller uuid := swasthyalens_private.report_require_user();
  document public.reports%rowtype;
  object_metadata jsonb;
  actual_size text;
begin
  select * into document from public.reports
    where id = p_report_id and user_id = caller for update;
  if not found then raise exception using errcode = 'P0001', message = 'report_not_found'; end if;
  if document.status = 'uploaded' then return to_jsonb(document); end if;
  if document.status <> 'uploading' or p_lease_token is null
    or document.lease_token is distinct from p_lease_token
    or document.upload_lease_expires_at <= statement_timestamp() then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  -- Metadata is read-only. Only the Storage API can create/delete object data.
  select metadata into object_metadata from storage.objects
    where bucket_id = 'reports' and name = document.storage_path;
  if not found then raise exception using errcode = 'P0001', message = 'report_conflict'; end if;
  actual_size := coalesce(object_metadata ->> 'size', object_metadata ->> 'contentLength');
  if actual_size is null or actual_size !~ '^[0-9]{1,16}$'
    or object_metadata ->> 'mimetype' is distinct from document.media_type then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  if actual_size::bigint <> document.size_bytes then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  update public.reports set status = 'uploaded', lease_token = null,
    upload_lease_expires_at = null, error_category = null
  where id = document.id and user_id = caller returning * into document;
  return to_jsonb(document);
end;
$$;

create function swasthyalens_private.report_fail_upload(
  p_report_id uuid, p_lease_token uuid, p_error_category text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  caller uuid := swasthyalens_private.report_require_user();
  document public.reports%rowtype;
begin
  select * into document from public.reports
    where id = p_report_id and user_id = caller for update;
  if not found then raise exception using errcode = 'P0001', message = 'report_not_found'; end if;
  if document.status in ('deleting', 'deleted') then return to_jsonb(document); end if;
  if p_error_category is null or p_error_category not in
    ('invalid_file', 'file_too_large', 'unsupported_file_type', 'filename_invalid',
      'storage_unavailable', 'metadata_unavailable', 'upload_interrupted', 'integrity_mismatch') then
    raise exception using errcode = 'P0001', message = 'invalid_file';
  end if;
  if document.status not in ('pending_upload', 'uploading', 'upload_failed')
    or (p_lease_token is null and (document.lease_token is not null or document.status = 'uploading'))
    or (p_lease_token is not null and document.lease_token is distinct from p_lease_token) then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  -- Deliberately retain lease/hash: an ambiguous HTTP failure is not proof that
  -- the provider stopped an in-flight upload.
  update public.reports set status = 'upload_failed', error_category = p_error_category
  where id = document.id and user_id = caller returning * into document;
  return to_jsonb(document);
end;
$$;

create function swasthyalens_private.report_begin_delete(p_report_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  caller uuid := swasthyalens_private.report_require_user();
  document public.reports%rowtype;
begin
  select * into document from public.reports
    where id = p_report_id and user_id = caller for update;
  if not found then raise exception using errcode = 'P0001', message = 'report_not_found'; end if;
  if document.status = 'deleted' then return to_jsonb(document); end if;
  update public.reports set status = 'deleting', error_category = null
  where id = document.id and user_id = caller returning * into document;
  return to_jsonb(document);
end;
$$;

create function swasthyalens_private.report_finish_delete(p_report_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  caller uuid := swasthyalens_private.report_require_user();
  document public.reports%rowtype;
begin
  select * into document from public.reports
    where id = p_report_id and user_id = caller for update;
  if not found then raise exception using errcode = 'P0001', message = 'report_not_found'; end if;
  if document.status not in ('deleting', 'deleted')
    or document.upload_lease_expires_at > statement_timestamp()
    or exists (select 1 from storage.objects
      where bucket_id = 'reports' and name = document.storage_path) then
    raise exception using errcode = 'P0001', message = 'report_conflict';
  end if;
  update public.reports set status = 'deleted', original_filename = null, media_type = null,
    size_bytes = null, sha256 = null, lease_token = null, upload_lease_expires_at = null,
    error_category = null, deleted_at = coalesce(deleted_at, statement_timestamp()),
    cleanup_checked_at = statement_timestamp()
  where id = document.id and user_id = caller returning * into document;
  return to_jsonb(document);
end;
$$;

create function swasthyalens_private.report_cleanup_candidates(p_limit integer default 10)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.report_require_user(); result jsonb;
begin
  if p_limit is null or p_limit not between 1 and 20 then
    raise exception using errcode = 'P0001', message = 'invalid_file';
  end if;
  select coalesce(jsonb_agg(to_jsonb(candidate)), '[]'::jsonb) into result from (
    select * from public.reports where user_id = caller and status in ('deleting', 'deleted')
      and (upload_lease_expires_at is null or upload_lease_expires_at <= statement_timestamp())
      and (cleanup_checked_at is null or cleanup_checked_at <= statement_timestamp() - interval '5 minutes')
    order by cleanup_checked_at asc nulls first, created_at, id limit p_limit
  ) as candidate;
  return result;
end;
$$;

create function swasthyalens_private.report_touch_cleanup(p_report_id uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.report_require_user();
begin
  update public.reports set cleanup_checked_at = statement_timestamp()
  where id = p_report_id and user_id = caller and status in ('deleting', 'deleted');
  if not found then raise exception using errcode = 'P0001', message = 'report_not_found'; end if;
end;
$$;

create function public.report_reserve(
  p_filename text, p_media_type text, p_size_bytes bigint, p_idempotency_key uuid)
returns jsonb language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_reserve(p_filename, p_media_type, p_size_bytes, p_idempotency_key);
$$;
create function public.report_begin_upload(p_report_id uuid, p_sha256 text)
returns jsonb language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_begin_upload(p_report_id, p_sha256);
$$;
create function public.report_finish_upload(p_report_id uuid, p_lease_token uuid)
returns jsonb language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_finish_upload(p_report_id, p_lease_token);
$$;
create function public.report_fail_upload(p_report_id uuid, p_lease_token uuid, p_error_category text)
returns jsonb language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_fail_upload(p_report_id, p_lease_token, p_error_category);
$$;
create function public.report_begin_delete(p_report_id uuid)
returns jsonb language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_begin_delete(p_report_id);
$$;
create function public.report_finish_delete(p_report_id uuid)
returns jsonb language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_finish_delete(p_report_id);
$$;
create function public.report_cleanup_candidates(p_limit integer default 10)
returns jsonb language sql stable security invoker set search_path = '' as $$
  select swasthyalens_private.report_cleanup_candidates(p_limit);
$$;
create function public.report_touch_cleanup(p_report_id uuid)
returns void language sql security invoker set search_path = '' as $$
  select swasthyalens_private.report_touch_cleanup(p_report_id);
$$;

create function swasthyalens_private.report_storage_access(p_path text, p_action text)
returns boolean language plpgsql stable security definer set search_path = '' as $$
declare caller uuid;
begin
  if not swasthyalens_private.session_is_active() then return false; end if;
  caller := auth.uid();
  return exists (
    select 1 from public.reports where user_id = caller and storage_path = p_path
      and ((p_action = 'upload' and status = 'uploading'
          and upload_lease_expires_at > statement_timestamp())
        or (p_action = 'read' and status in ('uploading', 'uploaded'))
        or (p_action = 'delete' and status in ('deleting', 'deleted')))
  );
end;
$$;

-- Final upload completion is provider-owned and can outlive its original RLS
-- authorization. Tombstones retain immutable paths for repeat API cleanup.
create policy swasthyalens_reports_insert on storage.objects for insert to authenticated
  with check (bucket_id = 'reports'
    and storage.allow_only_operation('object.upload')
    and swasthyalens_private.report_storage_access(name, 'upload'));
create policy swasthyalens_reports_select on storage.objects for select to authenticated
  using (bucket_id = 'reports' and (
    (storage.allow_any_operation(array['object.get_authenticated', 'object.get_authenticated_info',
      'object.head_authenticated_info'])
      and swasthyalens_private.report_storage_access(name, 'read'))
    or (storage.allow_only_operation('object.delete_many')
      and swasthyalens_private.report_storage_access(name, 'delete'))));
create policy swasthyalens_reports_delete on storage.objects for delete to authenticated
  using (bucket_id = 'reports' and storage.allow_only_operation('object.delete_many')
    and swasthyalens_private.report_storage_access(name, 'delete'));

-- Revoke PostgreSQL's default PUBLIC EXECUTE before any new function commits.
do $$
declare routine record;
begin
  for routine in select p.oid::regprocedure as signature
    from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('public', 'swasthyalens_private') and p.proname like 'report\_%' escape '\'
  loop
    execute format('revoke all on function %s from public, anon, authenticated, service_role', routine.signature);
    execute format('grant execute on function %s to authenticated', routine.signature);
  end loop;
end;
$$;

comment on table public.reports is
  'Private Phase 3 report manifest. No OCR/medical data. Deleted tombstones retain cleanup paths; owner deletion is restricted until an explicit cleanup/purge workflow exists.';
comment on column public.reports.sha256 is
  'Expected bytes digest, verified by the backend on retrieval. A database status never certifies file safety or medical interpretation.';
comment on function swasthyalens_private.report_storage_access(text, text) is
  'Current active JWT owner only. Upload/read/delete are narrowly allowed by lifecycle and Storage operation; no signing/overwrite/list/copy/move permissions.';

notify pgrst, 'reload schema';
commit;
