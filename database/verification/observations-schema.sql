-- Read-only schema and access assertions.
do $$ declare t text; begin
 foreach t in array array['health_observations','health_observation_revisions'] loop
  if not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relname=t and c.relrowsecurity and c.relforcerowsecurity) then
   raise exception 'Missing forced RLS: %',t; end if;
  if not has_table_privilege('authenticated','public.'||t,'SELECT')
   or has_table_privilege('authenticated','public.'||t,'INSERT,UPDATE,DELETE')
   or has_table_privilege('anon','public.'||t,'SELECT,INSERT,UPDATE,DELETE') then
   raise exception 'Unexpected table grants: %',t; end if;
 end loop;
 if not exists(select 1 from pg_indexes where indexname='observation_one_active' and indexdef like '%UNIQUE%WHERE%active%') then
  raise exception 'Missing single-active constraint'; end if;
 if has_function_privilege('anon','public.observation_call(text,jsonb,text)','EXECUTE')
 or has_function_privilege('authenticated','swasthyalens_private.observation_document(uuid,boolean)','EXECUTE')
 or not has_function_privilege('authenticated','public.observation_call(text,jsonb,text)','EXECUTE') then
  raise exception 'Unexpected function grants'; end if;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname='observation_call' and p.prosecdef) then
  raise exception 'Exposed definer function'; end if;
 if not exists(select 1 from pg_trigger where tgname='observation_review_invalidation' and not tgisinternal)
 or not exists(select 1 from pg_trigger where tgname='observation_snapshot_immutable' and not tgisinternal) then
  raise exception 'Missing lifecycle trigger'; end if;
end; $$;
select 'Phase 6 schema assertions passed.' as result;
