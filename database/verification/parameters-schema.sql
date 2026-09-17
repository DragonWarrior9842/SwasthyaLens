do $$ declare item text; begin
 foreach item in array array['report_parameter_runs','report_parameter_candidates','report_parameter_reviews'] loop
  if not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relname=item and c.relrowsecurity and c.relforcerowsecurity) then raise exception 'Missing forced RLS: %',item; end if;
  if has_table_privilege('anon','public.'||item,'SELECT') or has_table_privilege('authenticated','public.'||item,'INSERT') or has_table_privilege('authenticated','public.'||item,'UPDATE') or has_table_privilege('authenticated','public.'||item,'DELETE') then raise exception 'Unexpected table privilege: %',item; end if;
 end loop;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like 'parameter_%' and p.prosecdef) then raise exception 'Public parameter function must be invoker'; end if;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','swasthyalens_private') and p.proname like 'parameter_%' and has_function_privilege('anon',p.oid,'EXECUTE')) then raise exception 'Anonymous RPC grant'; end if;
 if not exists(select 1 from pg_indexes where schemaname='public' and indexname='parameter_run_source') then raise exception 'Composite FK index missing'; end if;
end; $$;
