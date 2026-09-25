begin;
do $$
declare item record;
begin
 for item in select p.*,n.nspname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where proname='trend_context' and n.nspname in ('public','swasthyalens_private') loop
  if item.prosecdef or item.provolatile<>'s' or not ('search_path=""'=any(item.proconfig)) then
   raise exception 'Trend function must be stable invoker with empty search path'; end if;
  if has_function_privilege('anon',item.oid,'EXECUTE') or has_function_privilege('service_role',item.oid,'EXECUTE')
   or not has_function_privilege('authenticated',item.oid,'EXECUTE') then
   raise exception 'Trend function grants invalid'; end if;
 end loop;
 if (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where proname='trend_context'
  and n.nspname in ('public','swasthyalens_private'))<>2 then raise exception 'Missing functions'; end if;
 if not exists(select 1 from pg_indexes where schemaname='public' and indexname='observation_metric_day_active')
  or not exists(select 1 from pg_indexes where schemaname='public' and indexname='observation_metric_instant_active')
  then raise exception 'Missing bounded query indexes'; end if;
end; $$;
rollback;
