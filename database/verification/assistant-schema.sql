begin;
do $$
declare t text;
begin
 foreach t in array array['assistant_conversations','assistant_messages'] loop
  if not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relname=t and c.relrowsecurity and c.relforcerowsecurity) then
   raise exception 'Assistant RLS missing'; end if;
  if not has_table_privilege('authenticated','public.'||t,'SELECT')
   or has_table_privilege('anon','public.'||t,'SELECT')
   or has_table_privilege('authenticated','public.'||t,'INSERT,UPDATE,DELETE')
   or has_table_privilege('service_role','public.'||t,'SELECT') then
   raise exception 'Assistant table grants invalid'; end if;
 end loop;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public' and p.proname='assistant_call' and p.prosecdef) then
  raise exception 'Exposed definer'; end if;
 if has_function_privilege('anon','public.assistant_call(text,jsonb,text)','EXECUTE')
  or has_function_privilege('service_role','public.assistant_call(text,jsonb,text)','EXECUTE') then
  raise exception 'Assistant RPC grants invalid'; end if;
 if not exists(select 1 from pg_constraint where conrelid='public.assistant_messages'::regclass
  and contype='f' and array_length(conkey,1)=2 and confdeltype='c') then
  raise exception 'Owner-consistent cascading parent key missing'; end if;
end; $$;
rollback;
