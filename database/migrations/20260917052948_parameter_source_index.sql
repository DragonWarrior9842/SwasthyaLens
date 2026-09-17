-- Cover the complete composite FK used when source attempts are deleted.
begin;
create index parameter_run_source on public.report_parameter_candidates(run_id, source_run_id);
commit;
