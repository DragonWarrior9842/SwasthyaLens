-- Read-only inspection. Run after the migration in Supabase SQL Editor.
-- All assertions fail closed; no identities, tokens or health records are read.
begin read only;

do $$
declare
  table_name text;
  owner_column text;
  actual_count integer;
begin
  foreach table_name in array array['profiles', 'user_settings'] loop
    owner_column := case when table_name = 'profiles' then 'id' else 'user_id' end;
    if not exists (
      select 1 from pg_catalog.pg_class c
      join pg_catalog.pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = table_name
        and c.relrowsecurity and c.relforcerowsecurity
    ) then
      raise exception 'RLS is not enabled and forced on %', table_name;
    end if;
    select count(*) into actual_count from pg_catalog.pg_policies
      where schemaname = 'public' and tablename = table_name
        and roles = array['authenticated']::name[]
        and cmd in ('SELECT', 'INSERT', 'UPDATE', 'DELETE');
    if actual_count <> 4 then
      raise exception 'Expected four authenticated policies on %', table_name;
    end if;
    select count(*) into actual_count from pg_catalog.pg_policies
      where schemaname = 'public' and tablename = table_name;
    if actual_count <> 4 then
      raise exception 'Unexpected additional policies on %', table_name;
    end if;
    if has_any_column_privilege('anon', 'public.' || table_name, 'SELECT,INSERT,UPDATE')
      or has_table_privilege('anon', 'public.' || table_name, 'DELETE,TRUNCATE') then
      raise exception 'Anonymous privileges detected on %', table_name;
    end if;
    if has_column_privilege('authenticated', 'public.' || table_name, owner_column, 'UPDATE')
      or has_column_privilege('authenticated', 'public.' || table_name, 'created_at', 'INSERT,UPDATE')
      or has_column_privilege('authenticated', 'public.' || table_name, 'updated_at', 'INSERT,UPDATE')
      or has_table_privilege('authenticated', 'public.' || table_name, 'TRUNCATE,TRIGGER') then
      raise exception 'Identity/audit/administrative privileges detected on %', table_name;
    end if;
    if not has_column_privilege('authenticated', 'public.' || table_name, owner_column, 'INSERT')
      or not has_table_privilege('authenticated', 'public.' || table_name, 'SELECT')
      or not has_table_privilege('authenticated', 'public.' || table_name, 'DELETE') then
      raise exception 'Required user-scoped privileges missing on %', table_name;
    end if;
    if not exists (
      select 1 from pg_catalog.pg_constraint con
      join pg_catalog.pg_attribute att on att.attrelid = con.conrelid
        and att.attnum = con.conkey[1]
      where con.conrelid = ('public.' || table_name)::regclass
        and con.contype = 'f' and con.confrelid = 'auth.users'::regclass
        and con.confdeltype = 'c' and att.attname = owner_column
    ) then
      raise exception 'Authoritative auth.users cascade foreign key missing on %', table_name;
    end if;
    if not exists (
      select 1 from pg_catalog.pg_trigger
      where tgrelid = ('public.' || table_name)::regclass
        and tgfoid = 'swasthyalens_private.set_updated_at()'::regprocedure
        and not tgisinternal and tgenabled = 'O' and tgtype = 19
    ) then
      raise exception 'Enabled BEFORE UPDATE row timestamp trigger missing on %', table_name;
    end if;
  end loop;

  if has_function_privilege('anon', 'public.session_context()', 'EXECUTE')
    or not has_function_privilege('authenticated', 'public.session_context()', 'EXECUTE') then
    raise exception 'Session RPC privileges are incorrect';
  end if;
  if not exists (select 1 from pg_catalog.pg_proc
      where oid = 'public.session_context()'::regprocedure
        and not prosecdef and proconfig @> array['search_path=""']) then
    raise exception 'Public session RPC must be invoker with fixed empty search path';
  end if;
  if not exists (select 1 from pg_catalog.pg_proc
      where oid = 'swasthyalens_private.current_session_context()'::regprocedure
        and prosecdef and pronargs = 0 and proconfig @> array['search_path=""']) then
    raise exception 'Private session helper contract is incorrect';
  end if;
  if has_schema_privilege('authenticated', 'swasthyalens_private', 'CREATE')
    or has_schema_privilege('anon', 'swasthyalens_private', 'USAGE') then
    raise exception 'Private schema privileges are incorrect';
  end if;
end;
$$;

select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public' and table_name in ('profiles', 'user_settings')
order by table_name, ordinal_position;

select c.relname as table_name, con.conname, pg_get_constraintdef(con.oid) as definition
from pg_catalog.pg_constraint con
join pg_catalog.pg_class c on c.oid = con.conrelid
join pg_catalog.pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname in ('profiles', 'user_settings')
order by table_name, con.conname;

select tablename, policyname, roles, cmd, qual, with_check
from pg_catalog.pg_policies
where schemaname = 'public' and tablename in ('profiles', 'user_settings')
order by tablename, cmd;

select table_name, grantee, column_name, privilege_type
from information_schema.column_privileges
where table_schema = 'public' and table_name in ('profiles', 'user_settings')
  and grantee in ('anon', 'authenticated')
order by table_name, grantee, column_name, privilege_type;

select n.nspname as schema_name, p.proname, p.prosecdef as security_definer,
  p.proconfig, p.proacl, pg_get_userbyid(p.proowner) as owner
from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'swasthyalens_private'
  or (n.nspname = 'public' and p.proname = 'session_context')
order by schema_name, p.proname;

select 'Phase 2 schema assertions passed; review the result sets and API exposure settings.' as result;
commit;
