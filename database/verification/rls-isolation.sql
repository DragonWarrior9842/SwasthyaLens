-- DEVELOPMENT DATABASE ONLY. Run the entire file, never selected statements.
-- This harness creates random test fixtures inside one ROLLBACK-only transaction.
-- It tests actual PostgreSQL privileges/RLS, not JWT signatures or email delivery.
-- No provider token is generated, and no pre-existing account is selected/changed.
begin;
set local statement_timeout = '30s';
set local lock_timeout = '5s';

create temporary table phase2_test_context (
  label text primary key,
  user_id uuid not null default gen_random_uuid(),
  session_id uuid not null default gen_random_uuid()
) on commit drop;
insert into phase2_test_context(label) values ('A'), ('B');
grant select on phase2_test_context to authenticated, anon;

insert into auth.users (id, aud, role, email, email_confirmed_at, created_at, updated_at)
select user_id, 'authenticated', 'authenticated', user_id::text || '@phase2-test.invalid',
  statement_timestamp(), statement_timestamp(), statement_timestamp()
from phase2_test_context;
insert into auth.sessions (id, user_id, created_at, updated_at)
select session_id, user_id, statement_timestamp() - interval '5 minutes', statement_timestamp()
from phase2_test_context;

create function pg_temp.assert_true(condition boolean, label text)
returns void language plpgsql security invoker as $$
begin
  if condition is distinct from true then
    raise exception 'FAILED: %', label;
  end if;
end;
$$;
create function pg_temp.expect_error(statement text, expected_state text, label text)
returns void language plpgsql security invoker as $$
begin
  begin
    execute statement;
  exception when others then
    if sqlstate = expected_state then return; end if;
    raise exception 'FAILED: %, expected SQLSTATE %, got %', label, expected_state, sqlstate;
  end;
  raise exception 'FAILED: %, statement unexpectedly succeeded', label;
end;
$$;

set local role authenticated;
do $$
declare
  actor record;
  other_user uuid;
  other_session uuid;
  claims jsonb;
  changed integer;
  old_created_at timestamptz;
begin
  perform pg_temp.assert_true(current_user = 'authenticated', 'tests use the real authenticated role');
  for actor in select * from pg_temp.phase2_test_context order by label loop
    select user_id, session_id into other_user, other_session
      from pg_temp.phase2_test_context where label <> actor.label;
    claims := jsonb_build_object('sub', actor.user_id, 'role', 'authenticated',
      'session_id', actor.session_id, 'is_anonymous', false);
    perform set_config('request.jwt.claims', claims::text, true);
    perform pg_temp.assert_true((public.session_context() ->> 'active')::boolean,
      actor.label || ' active provider session');
    perform pg_temp.assert_true((public.session_context() ->> 'expires_at')::bigint
      between extract(epoch from statement_timestamp() + interval '7 hours')::bigint
      and extract(epoch from statement_timestamp() + interval '8 hours')::bigint,
      actor.label || ' bounded absolute expiry');

    insert into public.profiles(id, display_name) values (actor.user_id, 'Fixture ' || actor.label);
    insert into public.user_settings(user_id) values (actor.user_id);
    insert into public.profiles(id) values (actor.user_id) on conflict (id) do nothing;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, actor.label || ' idempotent profile initialization');
    insert into public.user_settings(user_id) values (actor.user_id) on conflict (user_id) do nothing;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, actor.label || ' idempotent settings initialization');
    perform pg_temp.assert_true((select count(*) from public.profiles where id = actor.user_id) = 1,
      actor.label || ' own profile readable');
    perform pg_temp.assert_true((select count(*) from public.user_settings where user_id = actor.user_id) = 1,
      actor.label || ' own settings readable');

    perform pg_temp.expect_error(format('insert into public.profiles(id) values (%L)', other_user),
      '42501', actor.label || ' forged profile owner insert');
    perform pg_temp.expect_error(format('insert into public.user_settings(user_id) values (%L)', other_user),
      '42501', actor.label || ' forged settings owner insert');
    perform pg_temp.expect_error(format('update public.profiles set id = %L where id = %L',
      other_user, actor.user_id), '42501', actor.label || ' immutable profile identity');
    perform pg_temp.expect_error(format('update public.user_settings set user_id = %L where user_id = %L',
      other_user, actor.user_id), '42501', actor.label || ' immutable settings identity');

    perform pg_temp.expect_error(format('insert into public.profiles(id,created_at) values (%L,now())',
      actor.user_id), '42501', actor.label || ' profile created_at insert forgery');
    perform pg_temp.expect_error(format('insert into public.profiles(id,updated_at) values (%L,now())',
      actor.user_id), '42501', actor.label || ' profile updated_at insert forgery');
    perform pg_temp.expect_error(format('insert into public.user_settings(user_id,created_at) values (%L,now())',
      actor.user_id), '42501', actor.label || ' settings created_at insert forgery');
    perform pg_temp.expect_error(format('insert into public.user_settings(user_id,updated_at) values (%L,now())',
      actor.user_id), '42501', actor.label || ' settings updated_at insert forgery');
    perform pg_temp.expect_error('update public.profiles set created_at = now()',
      '42501', actor.label || ' profile created_at update forgery');
    perform pg_temp.expect_error('update public.profiles set updated_at = now()',
      '42501', actor.label || ' profile updated_at update forgery');
    perform pg_temp.expect_error('update public.user_settings set created_at = now()',
      '42501', actor.label || ' settings created_at update forgery');
    perform pg_temp.expect_error('update public.user_settings set updated_at = now()',
      '42501', actor.label || ' settings updated_at update forgery');

    perform pg_temp.expect_error('update public.profiles set display_name = '' ''',
      '23514', actor.label || ' blank display name');
    perform pg_temp.expect_error('update public.profiles set display_name = repeat(''x'',81)',
      '23514', actor.label || ' overlong display name');
    perform pg_temp.expect_error('update public.user_settings set preferred_language = ''fr''',
      '23514', actor.label || ' unsupported language');
    perform pg_temp.expect_error('update public.user_settings set timezone = ''Mars/Olympus''',
      '23514', actor.label || ' invented timezone');
    perform pg_temp.expect_error('update public.user_settings set timezone = ''+05:30''',
      '23514', actor.label || ' numeric timezone offset');
    perform pg_temp.expect_error('update public.user_settings set timezone = null',
      '23502', actor.label || ' null timezone');

    select created_at into old_created_at from public.profiles where id = actor.user_id;
    update public.profiles set display_name = 'Updated ' || actor.label where id = actor.user_id;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 1, actor.label || ' own profile update');
    perform pg_temp.assert_true((select created_at = old_created_at and updated_at >= created_at
      from public.profiles where id = actor.user_id), actor.label || ' server audit timestamps');
    update public.user_settings set preferred_language = 'hi', timezone = 'Asia/Kolkata'
      where user_id = actor.user_id;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 1, actor.label || ' own settings update');

    perform set_config('request.jwt.claims', (claims || '{"is_anonymous":true}'::jsonb)::text, true);
    perform pg_temp.assert_true(public.session_context() = '{"active":false,"expires_at":null}'::jsonb,
      actor.label || ' Supabase anonymous identity rejected');
    perform pg_temp.assert_true((select count(*) from public.profiles) = 0,
      actor.label || ' anonymous identity cannot read profiles');
    perform set_config('request.jwt.claims', (claims || jsonb_build_object('session_id', other_session))::text, true);
    perform pg_temp.assert_true(not (public.session_context() ->> 'active')::boolean,
      actor.label || ' other user session cannot be substituted');
    perform set_config('request.jwt.claims', (claims || '{"session_id":"malformed"}'::jsonb)::text, true);
    perform pg_temp.assert_true(not (public.session_context() ->> 'active')::boolean,
      actor.label || ' malformed session safely rejected');
    perform set_config('request.jwt.claims', (claims - 'session_id')::text, true);
    perform pg_temp.assert_true(not (public.session_context() ->> 'active')::boolean,
      actor.label || ' missing session rejected');
    perform set_config('request.jwt.claims', (claims || '{"sub":"malformed"}'::jsonb)::text, true);
    perform pg_temp.assert_true(not (public.session_context() ->> 'active')::boolean,
      actor.label || ' malformed subject safely rejected by RPC');
    perform set_config('request.jwt.claims', claims::text, true);
    perform pg_temp.expect_error('select * from auth.sessions', '42501',
      actor.label || ' cannot read provider sessions directly');
  end loop;

  -- Both rows now exist: prove isolation in both directions and check row counts.
  for actor in select * from pg_temp.phase2_test_context order by label loop
    select user_id into other_user from pg_temp.phase2_test_context where label <> actor.label;
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    perform pg_temp.assert_true((select count(*) from public.profiles) = 1,
      actor.label || ' profile list isolates one owner');
    perform pg_temp.assert_true((select count(*) from public.user_settings) = 1,
      actor.label || ' settings list isolates one owner');
    perform pg_temp.assert_true((select count(*) from public.profiles where id = other_user) = 0,
      actor.label || ' cross-user profile read denied');
    perform pg_temp.assert_true((select count(*) from public.user_settings where user_id = other_user) = 0,
      actor.label || ' cross-user settings read denied');
    update public.profiles set display_name = 'Forbidden' where id = other_user;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, actor.label || ' cross-user profile update denied');
    update public.user_settings set preferred_language = 'en' where user_id = other_user;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, actor.label || ' cross-user settings update denied');
    delete from public.profiles where id = other_user;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, actor.label || ' cross-user profile delete denied');
    delete from public.user_settings where user_id = other_user;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, actor.label || ' cross-user settings delete denied');
  end loop;
end;
$$;
reset role;

-- Confirm stored data, not just an HTTP-style zero-row response.
select pg_temp.assert_true((select count(*) from public.profiles p
  join pg_temp.phase2_test_context t on t.user_id = p.id
  where p.display_name = 'Updated ' || t.label) = 2, 'both stored profiles survived IDOR attempts');
select pg_temp.assert_true((select count(*) from public.user_settings s
  join pg_temp.phase2_test_context t on t.user_id = s.user_id
  where s.preferred_language = 'hi' and s.timezone = 'Asia/Kolkata') = 2,
  'both stored settings survived IDOR attempts');

-- Actual session rows are time-limited inside this transaction only.
update auth.sessions set not_after = statement_timestamp() + interval '30 minutes'
where id = (select session_id from phase2_test_context where label = 'B');
set local role authenticated;
do $$
declare actor record;
begin
  select * into actor from pg_temp.phase2_test_context where label = 'B';
  perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
    'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
  perform pg_temp.assert_true((public.session_context() ->> 'active')::boolean,
    'future provider not_after still permits the session');
  perform pg_temp.assert_true((public.session_context() ->> 'expires_at')::bigint
    between extract(epoch from statement_timestamp() + interval '29 minutes')::bigint
    and extract(epoch from statement_timestamp() + interval '31 minutes')::bigint,
    'earlier future provider not_after bounds the returned expiry');
end;
$$;
reset role;
update auth.sessions set created_at = statement_timestamp() - interval '8 hours'
where id = (select session_id from phase2_test_context where label = 'A');
update auth.sessions set not_after = statement_timestamp() - interval '1 second'
where id = (select session_id from phase2_test_context where label = 'B');
set local role authenticated;
do $$
declare actor record; changed integer;
begin
  for actor in select * from pg_temp.phase2_test_context loop
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    perform pg_temp.assert_true(public.session_context() = '{"active":false,"expires_at":null}'::jsonb,
      actor.label || ' absolute lifetime/provider not_after enforced');
    perform pg_temp.assert_true((select count(*) from public.profiles) = 0, 'expired profile reads denied');
    perform pg_temp.assert_true((select count(*) from public.user_settings) = 0, 'expired settings reads denied');
    update public.profiles set display_name = 'Forbidden';
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'expired profile update denied');
    update public.user_settings set preferred_language = 'en';
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'expired settings update denied');
    delete from public.profiles;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'expired profile delete denied');
    delete from public.user_settings;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'expired settings delete denied');
    perform pg_temp.expect_error(format('insert into public.profiles(id) values (%L)', actor.user_id),
      '42501', 'expired profile insert denied');
    perform pg_temp.expect_error(format('insert into public.user_settings(user_id) values (%L)', actor.user_id),
      '42501', 'expired settings insert denied');
  end loop;
end;
$$;
reset role;

-- Revocation removes actual provider-session rows. Replayed claims must fail.
-- First restore and prove these sessions are ACTIVE, so timeout cannot mask a
-- broken revocation check. Only the two random fixtures are affected.
update auth.sessions set created_at = statement_timestamp() - interval '5 minutes', not_after = null
where id in (select session_id from phase2_test_context);
set local role authenticated;
do $$
declare actor record;
begin
  for actor in select * from pg_temp.phase2_test_context loop
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    perform pg_temp.assert_true((public.session_context() ->> 'active')::boolean,
      'revocation fixture starts active');
  end loop;
end;
$$;
reset role;
delete from auth.sessions where id in (select session_id from phase2_test_context);
set local role authenticated;
do $$
declare actor record; changed integer;
begin
  for actor in select * from pg_temp.phase2_test_context loop
    perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
      'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
    perform pg_temp.assert_true(not (public.session_context() ->> 'active')::boolean, 'revoked session rejected');
    perform pg_temp.assert_true((select count(*) from public.profiles) = 0, 'revoked profile reads denied');
    perform pg_temp.assert_true((select count(*) from public.user_settings) = 0, 'revoked settings reads denied');
    update public.user_settings set preferred_language = 'en';
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'revoked settings update denied');
    update public.profiles set display_name = 'Forbidden';
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'revoked profile update denied');
    delete from public.profiles;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'revoked profile delete denied');
    delete from public.user_settings;
    get diagnostics changed = row_count;
    perform pg_temp.assert_true(changed = 0, 'revoked settings delete denied');
    perform pg_temp.expect_error(format('insert into public.profiles(id) values (%L)', actor.user_id),
      '42501', 'revoked profile insert denied');
    perform pg_temp.expect_error(format('insert into public.user_settings(user_id) values (%L)', actor.user_id),
      '42501', 'revoked settings insert denied');
  end loop;
end;
$$;
reset role;

-- Grant-level rejection for genuinely unauthenticated Data API requests.
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);
select pg_temp.expect_error('select * from public.profiles', '42501', 'anon profile read');
select pg_temp.expect_error('select * from public.user_settings', '42501', 'anon settings read');
select pg_temp.expect_error('insert into public.profiles(id) values (gen_random_uuid())', '42501', 'anon insert');
select pg_temp.expect_error('insert into public.user_settings(user_id) values (gen_random_uuid())',
  '42501', 'anon settings insert');
select pg_temp.expect_error('update public.profiles set display_name = null', '42501', 'anon update');
select pg_temp.expect_error('update public.user_settings set preferred_language = ''en''',
  '42501', 'anon settings update');
select pg_temp.expect_error('delete from public.profiles', '42501', 'anon profile delete');
select pg_temp.expect_error('delete from public.user_settings', '42501', 'anon delete');
select pg_temp.expect_error('select public.session_context()', '42501', 'anon session RPC');
reset role;

-- Restore only our fixture sessions to test permitted owner deletes and FK cascade.
insert into auth.sessions(id, user_id, created_at, updated_at)
select session_id, user_id, statement_timestamp(), statement_timestamp() from phase2_test_context;
set local role authenticated;
do $$
declare actor record; changed integer;
begin
  select * into actor from pg_temp.phase2_test_context where label = 'A';
  perform set_config('request.jwt.claims', jsonb_build_object('sub', actor.user_id,
    'role', 'authenticated', 'session_id', actor.session_id, 'is_anonymous', false)::text, true);
  delete from public.profiles where id = actor.user_id;
  get diagnostics changed = row_count;
  perform pg_temp.assert_true(changed = 1, 'owner may delete own profile');
  delete from public.user_settings where user_id = actor.user_id;
  get diagnostics changed = row_count;
  perform pg_temp.assert_true(changed = 1, 'owner may delete own settings');
end;
$$;
reset role;
delete from auth.users where id = (select user_id from phase2_test_context where label = 'B');
select pg_temp.assert_true((select count(*) from public.profiles where id in
  (select user_id from phase2_test_context)) = 0, 'authoritative auth user cascade removes profile');
select pg_temp.assert_true((select count(*) from public.user_settings where user_id in
  (select user_id from phase2_test_context)) = 0, 'authoritative auth user cascade removes settings');

select 'Phase 2 database isolation assertions passed; all test fixtures are rolled back next.' as result;
rollback;
