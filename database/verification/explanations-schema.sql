begin;
do $$
declare name text;
begin
 foreach name in array array['public.report_explanations','swasthyalens_private.explanation_budget','swasthyalens_private.explanation_attempts','swasthyalens_private.explanation_evaluation_reports'] loop
  if not exists(select 1 from pg_class where oid=name::regclass and relrowsecurity and relforcerowsecurity) then raise exception 'Missing forced RLS: %',name; end if;
  if has_table_privilege('anon',name,'SELECT') or has_table_privilege('authenticated',name,'INSERT,UPDATE,DELETE') then raise exception 'Unsafe table grants: %',name; end if;
 end loop;
 if has_function_privilege('anon','public.explanation_call(text,jsonb,text)','EXECUTE')
  or not has_function_privilege('authenticated','public.explanation_call(text,jsonb,text)','EXECUTE')
  or has_function_privilege('authenticated','swasthyalens_private.explanation_cleanup()','EXECUTE') then raise exception 'Unsafe function grants'; end if;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','swasthyalens_private') and p.proname like 'explanation_%' and not coalesce(p.proconfig @> array['search_path=""'],false)) then raise exception 'Unsafe function search path'; end if;
 if not exists(select 1 from cron.job where jobname='swasthyalens-explanation-retention' and active and schedule='17 * * * *') then raise exception 'Retention job missing'; end if;
 if not exists(select 1 from swasthyalens_private.explanation_budget where id and reserved_cents between 0 and 500) then raise exception 'Budget safeguard missing'; end if;
end; $$;
rollback;
