-- SwasthyaLens Phase 2. Apply once, in order, as the project database owner.
-- No auth.users/auth.sessions data is created or modified by this migration.
begin;

-- Fail before creating objects if the expected provider session contract is
-- unavailable. LIMIT 0 verifies columns/privileges without reading account data.
do $$
begin
  perform id, user_id, created_at, not_after from auth.sessions limit 0;
end;
$$;

create schema swasthyalens_private;
revoke all on schema swasthyalens_private from public, anon, authenticated;
grant usage on schema swasthyalens_private to authenticated;
alter default privileges in schema swasthyalens_private revoke execute on functions from public;

-- This is the only privileged reader of provider session metadata. It accepts
-- no identity arguments and never returns provider rows, tokens or other users.
create function swasthyalens_private.current_session_context()
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  claims jsonb := auth.jwt();
  caller_id uuid;
  caller_session_id uuid;
  session_text text := claims ->> 'session_id';
  session_created_at timestamptz;
  session_expires_at timestamptz;
  inactive constant jsonb := '{"active":false,"expires_at":null}'::jsonb;
begin
  if claims ->> 'role' is distinct from 'authenticated'
    or coalesce(claims ->> 'is_anonymous', 'false') <> 'false'
    or session_text is null
    or session_text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  then
    return inactive;
  end if;

  begin
    caller_id := auth.uid();
    caller_session_id := session_text::uuid;
  exception when invalid_text_representation then
    return inactive;
  end;

  if caller_id is null then
    return inactive;
  end if;

  select sessions.created_at,
    least(sessions.created_at + interval '8 hours',
      coalesce(sessions.not_after, sessions.created_at + interval '8 hours'))
    into session_created_at, session_expires_at
  from auth.sessions as sessions
  where sessions.id = caller_session_id and sessions.user_id = caller_id;

  if not found or session_created_at is null or session_expires_at is null
    or session_created_at > statement_timestamp()
    or session_expires_at <= statement_timestamp()
  then
    return inactive;
  end if;

  return jsonb_build_object('active', true,
    'expires_at', floor(extract(epoch from session_expires_at))::bigint);
end;
$$;

create function swasthyalens_private.session_is_active()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select (swasthyalens_private.current_session_context() ->> 'active')::boolean;
$$;

-- Only this invoker wrapper is exposed through the public Data API schema.
create function public.session_context()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
  select swasthyalens_private.current_session_context();
$$;

revoke all on function swasthyalens_private.current_session_context()
  from public, anon, authenticated, service_role;
revoke all on function swasthyalens_private.session_is_active()
  from public, anon, authenticated, service_role;
revoke all on function public.session_context()
  from public, anon, authenticated, service_role;
grant execute on function swasthyalens_private.current_session_context() to authenticated;
grant execute on function swasthyalens_private.session_is_active() to authenticated;
grant execute on function public.session_context() to authenticated;

-- pg_timezone_names uses the server's IANA time-zone database. Reject offsets,
-- invented zones, whitespace and platform-specific posix/right aliases.
create function swasthyalens_private.is_valid_timezone(value text)
returns boolean
language sql
stable
strict
security invoker
set search_path = ''
as $$
  select char_length(value) between 1 and 128
    and value = btrim(value)
    and value !~ '^(posix|right)/'
    and exists (select 1 from pg_catalog.pg_timezone_names as zones where zones.name = value);
$$;
revoke all on function swasthyalens_private.is_valid_timezone(text)
  from public, anon, authenticated, service_role;
grant execute on function swasthyalens_private.is_valid_timezone(text) to authenticated;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default statement_timestamp(),
  updated_at timestamptz not null default statement_timestamp(),
  constraint profiles_display_name_valid check (
    display_name is null or (
      display_name = btrim(display_name)
      and char_length(display_name) between 1 and 80
      and display_name !~ '[[:cntrl:]]'
    )
  )
);

create table public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  preferred_language text not null default 'en',
  timezone text not null default 'UTC',
  created_at timestamptz not null default statement_timestamp(),
  updated_at timestamptz not null default statement_timestamp(),
  constraint user_settings_language_valid check (preferred_language in ('en', 'hi')),
  constraint user_settings_timezone_valid check (swasthyalens_private.is_valid_timezone(timezone))
);

create function swasthyalens_private.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at := statement_timestamp();
  return new;
end;
$$;
revoke all on function swasthyalens_private.set_updated_at()
  from public, anon, authenticated, service_role;

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function swasthyalens_private.set_updated_at();
create trigger user_settings_set_updated_at
before update on public.user_settings
for each row execute function swasthyalens_private.set_updated_at();

alter table public.profiles enable row level security;
alter table public.profiles force row level security;
alter table public.user_settings enable row level security;
alter table public.user_settings force row level security;

-- Remove permissive Supabase default grants before granting individual columns.
revoke all on table public.profiles, public.user_settings
  from public, anon, authenticated, service_role;
grant select, delete on table public.profiles, public.user_settings to authenticated;
grant insert (id, display_name) on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;
grant insert (user_id, preferred_language, timezone) on public.user_settings to authenticated;
grant update (preferred_language, timezone) on public.user_settings to authenticated;

create policy profiles_select_own_active on public.profiles for select to authenticated
  using (id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy profiles_insert_own_active on public.profiles for insert to authenticated
  with check (id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy profiles_update_own_active on public.profiles for update to authenticated
  using (id = (select auth.uid()) and (select swasthyalens_private.session_is_active()))
  with check (id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy profiles_delete_own_active on public.profiles for delete to authenticated
  using (id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));

create policy user_settings_select_own_active on public.user_settings for select to authenticated
  using (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy user_settings_insert_own_active on public.user_settings for insert to authenticated
  with check (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy user_settings_update_own_active on public.user_settings for update to authenticated
  using (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()))
  with check (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy user_settings_delete_own_active on public.user_settings for delete to authenticated
  using (user_id = (select auth.uid()) and (select swasthyalens_private.session_is_active()));

comment on schema swasthyalens_private is
  'SwasthyaLens helpers. Never add this schema to Supabase exposed API schemas.';
comment on function public.session_context() is
  'Current verified JWT session only: active status and absolute Unix expiry. No arguments.';
comment on table public.profiles is
  'Phase 2 profile keyed directly to Supabase auth.users; no health data.';
comment on table public.user_settings is
  'Phase 2 user preferences keyed directly to Supabase auth.users; no health data.';

notify pgrst, 'reload schema';
commit;
