-- Read-only Phase 3 schema assertions. No account/report contents are selected.
begin read only;

do $$
declare
  signature text;
begin
  if not exists (
    select 1 from pg_catalog.pg_class
    where oid = 'public.reports'::regclass and relrowsecurity and relforcerowsecurity
  ) then
    raise exception 'reports must enable and force RLS';
  end if;
  if not exists (
    select 1 from pg_catalog.pg_constraint
    where conrelid = 'public.reports'::regclass and contype = 'f'
      and confrelid = 'auth.users'::regclass and confdeltype = 'r'
  ) then
    raise exception 'reports must retain its authoritative owner until cleanup obligations end';
  end if;
  if has_any_column_privilege('anon', 'public.reports', 'SELECT,INSERT,UPDATE')
    or has_table_privilege('anon', 'public.reports', 'DELETE,TRUNCATE,TRIGGER')
    or has_any_column_privilege('authenticated', 'public.reports', 'INSERT,UPDATE')
    or has_table_privilege('authenticated', 'public.reports', 'DELETE,TRUNCATE,TRIGGER')
    or not has_table_privilege('authenticated', 'public.reports', 'SELECT') then
    raise exception 'reports grants must be authenticated SELECT only';
  end if;
  if (select count(*) from pg_catalog.pg_policies
      where schemaname = 'public' and tablename = 'reports') <> 4
    or (select count(*) from pg_catalog.pg_policies
      where schemaname = 'public' and tablename = 'reports'
        and roles = array['authenticated']::name[]) <> 4 then
    raise exception 'Unexpected reports policies';
  end if;
  if not exists (
    select 1 from storage.buckets where id = 'reports' and name = 'reports'
      and public is false and file_size_limit = 5242880
      and allowed_mime_types @> array['application/pdf', 'image/jpeg', 'image/png']::text[]
      and cardinality(allowed_mime_types) = 3
  ) then
    raise exception 'reports bucket must be private and limited to 5 MiB PDF/JPEG/PNG';
  end if;
  if (select count(*) from pg_catalog.pg_policies where schemaname = 'storage'
      and tablename = 'objects' and policyname like 'swasthyalens_reports_%') <> 3
    or exists (select 1 from pg_catalog.pg_policies where schemaname = 'storage'
      and tablename = 'objects' and policyname like 'swasthyalens_reports_%'
      and (cmd not in ('SELECT', 'INSERT', 'DELETE')
        or roles <> array['authenticated']::name[])) then
    raise exception 'Unexpected reports Storage policy surface';
  end if;
  foreach signature in array array[
    'report_reserve(text,text,bigint,uuid)',
    'report_begin_upload(uuid,text)',
    'report_finish_upload(uuid,uuid)',
    'report_fail_upload(uuid,uuid,text)',
    'report_begin_delete(uuid)',
    'report_finish_delete(uuid)',
    'report_cleanup_candidates(integer)',
    'report_touch_cleanup(uuid)'
  ] loop
    if has_function_privilege('anon', 'public.' || signature, 'EXECUTE')
      or not has_function_privilege('authenticated', 'public.' || signature, 'EXECUTE')
      or not exists (
        select 1 from pg_catalog.pg_proc
        where oid = ('public.' || signature)::regprocedure
          and not prosecdef and proconfig @> array['search_path=""']
      )
      or not exists (
        select 1 from pg_catalog.pg_proc
        where oid = ('swasthyalens_private.' || signature)::regprocedure
          and prosecdef and proconfig @> array['search_path=""']
      ) then
      raise exception 'Unsafe or missing report RPC: %', signature;
    end if;
  end loop;
  if has_schema_privilege('authenticated', 'swasthyalens_private', 'CREATE')
    or has_schema_privilege('anon', 'swasthyalens_private', 'USAGE') then
    raise exception 'Private schema privileges changed';
  end if;
end;
$$;

select 'Phase 3 reports schema assertions passed.' as result;
commit;
