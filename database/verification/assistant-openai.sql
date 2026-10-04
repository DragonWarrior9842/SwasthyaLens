begin;
do $$
declare expression text; pair record; accepted boolean;
begin
 select pg_get_expr(conbin,conrelid) into strict expression from pg_constraint
 where conrelid='public.assistant_messages'::regclass and conname='assistant_messages_check1';
 for pair in select * from (values
  ('openai','gpt-6.1-sol',true), ('openai','gpt-5.6-terra',false),
  ('gemini','gpt-6.1-sol',false), ('gemini','gemini-3.8-flash',true),
  ('mock-test','deterministic-test',true), ('rules','rules-v1',true),
  ('unknown','gpt-6.1-sol',false)
 ) as cases(provider,model,expected) loop
  execute format('select coalesce((%s),false) from (values ($1::text,$2::text)) as row(provider,model)',expression)
  into accepted using pair.provider,pair.model;
  if accepted is distinct from pair.expected then raise exception 'Provider model contract mismatch'; end if;
 end loop;
 if exists(select 1 from pg_class where oid in
  ('public.assistant_messages'::regclass,'public.assistant_conversations'::regclass)
  and (not relrowsecurity or not relforcerowsecurity)) then raise exception 'RLS missing'; end if;
 if has_table_privilege('authenticated','public.assistant_messages','INSERT,UPDATE,DELETE')
  or has_table_privilege('anon','public.assistant_messages','SELECT') then
  raise exception 'Assistant privileges broadened'; end if;
end $$;
rollback;
