-- Read-only Phase 11 boundary assertions.
begin;
do $$
begin
 if not exists(select 1 from pg_class where oid='public.notifications'::regclass and relrowsecurity and relforcerowsecurity)
 then raise exception 'Notifications must force RLS'; end if;
 if not has_table_privilege('authenticated','public.notifications','SELECT')
 or has_table_privilege('authenticated','public.notifications','INSERT,UPDATE,DELETE,TRUNCATE')
 or has_table_privilege('anon','public.notifications','SELECT,INSERT,UPDATE,DELETE')
 then raise exception 'Unexpected notification grants'; end if;
 if (select count(*) from pg_policies where schemaname='public' and tablename='notifications')<>1
 then raise exception 'Unexpected notification policies'; end if;
 if not has_column_privilege('authenticated','public.user_settings','in_app_notifications','UPDATE')
 then raise exception 'Missing owned preference grant'; end if;
 if exists(select 1 from pg_proc where oid in ('public.export_context(date,date,boolean,text,uuid)'::regprocedure,
  'swasthyalens_private.export_context(date,date,boolean,text,uuid)'::regprocedure,
  'public.notification_call(text,uuid,integer,text)'::regprocedure) and prosecdef)
 then raise exception 'Public/export functions must be invokers'; end if;
 if has_function_privilege('anon','public.export_context(date,date,boolean,text,uuid)','EXECUTE')
 or has_function_privilege('anon','public.notification_call(text,uuid,integer,text)','EXECUTE')
 or has_function_privilege('authenticated','swasthyalens_private.notification_event()','EXECUTE')
 or has_function_privilege('authenticated','swasthyalens_private.notification_cleanup()','EXECUTE')
 then raise exception 'Unexpected helper grants'; end if;
 if not exists(select 1 from cron.job where jobname='swasthyalens-notification-retention' and active)
 then raise exception 'Retention job missing'; end if;
end; $$;
rollback;
