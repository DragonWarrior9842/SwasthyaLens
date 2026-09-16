do $$
begin
  if (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
      where n.nspname='public' and c.relname in ('report_processing_runs','report_pages')
      and c.relrowsecurity and c.relforcerowsecurity) <> 2 then
    raise exception 'Derived RLS missing'; end if;
  if has_table_privilege('authenticated','public.report_pages','INSERT')
      or has_table_privilege('authenticated','public.report_processing_runs','UPDATE')
      or has_table_privilege('anon','public.report_pages','SELECT')
      or has_table_privilege('authenticated','swasthyalens_private.processing_key','SELECT') then
    raise exception 'Unexpected processing privilege'; end if;
  if not exists(select 1 from pg_trigger where tgname='report_erase_extraction' and not tgisinternal) then
    raise exception 'Deletion cleanup trigger missing'; end if;
  if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='public' and p.proname like 'processing_%' and p.prosecdef) then
    raise exception 'Public processing function must be invoker'; end if;
end; $$;
