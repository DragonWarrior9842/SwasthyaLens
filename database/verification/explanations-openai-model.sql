-- Run after explanation_model_metadata; no provider calls or permanent mutations.
begin;
do $$
declare expression text; pair record; accepted boolean; definition text;
begin
 select pg_get_expr(conbin,conrelid) into strict expression from pg_constraint
 where conrelid='public.report_explanations'::regclass
 and conname='explanation_provider_model_check';
 for pair in select * from (values
  ('openai','gpt-6.1-sol',true), ('openai','gpt-5.6-terra',true),
  ('mock-test','gpt-5.6-terra',true), ('mock-test','gpt-6.1-sol',false),
  ('gemini','gemini-3.8-flash',true), ('gemini','gpt-6.1-sol',false),
  ('openai','unknown-model',false)
 ) as cases(provider,model,expected) loop
  execute format('select coalesce((%s),false) from (values ($1::text,$2::text)) as row(provider,model)',expression)
  into accepted using pair.provider,pair.model;
  if accepted is distinct from pair.expected then raise exception 'Provider model mismatch'; end if;
 end loop;
 select pg_get_functiondef('swasthyalens_private.explanation_call(text,jsonb,text)'::regprocedure)
 into strict definition;
 if position('record.model<>selected_model' in definition)=0
  or position('e.model=selected_model' in definition)=0
  or position('mode,selected_model,' in definition)=0 then
  raise exception 'Model reservation/reuse checks missing'; end if;
 if not exists(select 1 from pg_class where oid='public.report_explanations'::regclass
  and relrowsecurity and relforcerowsecurity)
  or has_table_privilege('authenticated','public.report_explanations','INSERT,UPDATE,DELETE')
  or has_table_privilege('anon','public.report_explanations','SELECT') then
  raise exception 'Explanation authorization changed'; end if;
 if exists(select 1 from pg_proc where oid='public.explanation_call(text,jsonb,text)'::regprocedure
  and prosecdef) then raise exception 'Public invoker changed'; end if;
end $$;
rollback;
