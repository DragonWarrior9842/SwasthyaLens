-- Permit only the explicitly selected OpenAI pair. No RLS/RPC/grant changes.
begin;
alter table public.assistant_messages
 drop constraint assistant_messages_provider_check,
 drop constraint assistant_messages_check1;
alter table public.assistant_messages
 add constraint assistant_messages_provider_check
 check (provider in ('gemini','openai','mock-test','rules')),
 add constraint assistant_messages_check1
 check ((provider is null and model is null)
  or (provider='gemini' and model='gemini-3.8-flash')
  or (provider='openai' and model='gpt-6.1-sol')
  or (provider='mock-test' and model='deterministic-test')
  or (provider='rules' and model='rules-v1'));
commit;
