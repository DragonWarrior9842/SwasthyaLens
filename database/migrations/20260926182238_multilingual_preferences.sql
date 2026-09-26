-- Phase 10: preferences and frozen response language. Existing message bodies
-- and source provenance remain unchanged. Existing ownership/RLS/grants remain.
begin;
alter table public.user_settings add column assistant_language text not null default 'en'
 constraint user_settings_assistant_language_valid check(assistant_language in ('en','hi','hinglish'));
grant insert(assistant_language),update(assistant_language) on public.user_settings to authenticated;
alter table public.assistant_messages add column response_language text not null default 'en'
 constraint assistant_messages_language_valid check(response_language in ('en','hi','hinglish'));
alter table public.assistant_messages drop constraint assistant_messages_prompt_version_check;
alter table public.assistant_messages drop constraint assistant_messages_schema_version_check;
alter table public.assistant_messages add constraint assistant_messages_versions_valid check(
 (prompt_version='assistant-evidence-v1' and schema_version='assistant-closed-v1' and response_language='en')
 or (prompt_version='assistant-evidence-v2' and schema_version='assistant-closed-v2'));
alter table public.assistant_messages alter column prompt_version set default 'assistant-evidence-v2';
alter table public.assistant_messages alter column schema_version set default 'assistant-closed-v2';
-- No new source invalidation trigger: only actual timezone changes invalidate.
create or replace function swasthyalens_private.assistant_call(p_operation text,p_payload jsonb,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
 c public.assistant_conversations%rowtype; m public.assistant_messages%rowtype;
 key uuid; language text; created boolean:=false; items jsonb; source jsonb; body jsonb;
begin
 if p_operation='request' then
  perform pg_advisory_xact_lock(hashtextextended('assistant-generation',0));
 end if;
 perform pg_advisory_xact_lock(hashtextextended('assistant-owner:'||caller::text,0));
 update public.assistant_messages set status='failed',error_category='interrupted'
  where user_id=caller and status='generating' and created_at<statement_timestamp()-interval '90 seconds';
 if p_operation='list' then
  select coalesce(jsonb_agg(to_jsonb(q) order by q.updated_at desc,q.id),'[]') into items
   from (select id,created_at,updated_at from public.assistant_conversations where user_id=caller
    order by updated_at desc,id limit 20) q;
  return jsonb_build_object('user_id',caller,'conversations',items);
 elsif p_operation='create' then
  key:=(p_payload->>'idempotency_key')::uuid;
  if key is null or key='00000000-0000-0000-0000-000000000000'::uuid then
   raise exception using errcode='P0001',message='assistant_conflict'; end if;
  select * into c from public.assistant_conversations where user_id=caller and idempotency_key=key;
  if not found then
   if (select count(*) from public.assistant_conversations where user_id=caller)>=20 then
    raise exception using errcode='P0001',message='assistant_capacity'; end if;
   insert into public.assistant_conversations(user_id,idempotency_key) values(caller,key) returning * into c;
  end if;
 else
  select * into c from public.assistant_conversations where id=(p_payload->>'id')::uuid and user_id=caller for update;
  if not found then raise exception using errcode='P0001',message='assistant_not_found'; end if;
 end if;
 if p_operation='delete' then
  delete from public.assistant_conversations where id=c.id and user_id=caller;
  return jsonb_build_object('user_id',caller,'deleted',c.id);
 elsif p_operation='request' then
  key:=(p_payload->>'idempotency_key')::uuid;
  if key is null or key='00000000-0000-0000-0000-000000000000'::uuid
   or length(btrim(p_payload->>'content')) not between 1 and 2000 or p_payload->>'content' is null then
   raise exception using errcode='P0001',message='assistant_conflict'; end if;
  select * into m from public.assistant_messages where conversation_id=c.id and idempotency_key=key and role='user';
  if found then
   if m.content is distinct from p_payload->>'content' then
    raise exception using errcode='P0001',message='assistant_conflict'; end if;
  else
   if (select count(*) from public.assistant_messages where conversation_id=c.id)>=50 then
    raise exception using errcode='P0001',message='assistant_capacity'; end if;
   if exists(select 1 from public.assistant_messages where user_id=caller and status='generating')
    or (select count(*) from public.assistant_messages where status='generating' and created_at>=statement_timestamp()-interval '90 seconds')>=2
    or (select count(*) from public.assistant_messages where user_id=caller and role='user' and created_at>=statement_timestamp()-interval '1 minute')>=6
    or (select count(*) from public.assistant_messages where user_id=caller and role='user' and created_at>=statement_timestamp()-interval '1 day')>=100 then
    raise exception using errcode='P0001',message='assistant_rate_limit'; end if;
   -- Freeze the current saved preference under the settings row lock. A replay
   -- returns the original turn without consulting the current preference.
   select coalesce(p_payload->>'response_language',s.assistant_language) into language
    from public.user_settings s where s.user_id=caller for share;
   language:=coalesce(language,p_payload->>'response_language','en');
   if language not in ('en','hi','hinglish') then
    raise exception using errcode='P0001',message='assistant_conflict'; end if;
   insert into public.assistant_messages(user_id,conversation_id,idempotency_key,role,status,content,source_version,response_language)
    values(caller,c.id,key,'user','received',p_payload->>'content',c.source_version,language);
   insert into public.assistant_messages(user_id,conversation_id,idempotency_key,role,status,source_version,response_language)
    values(caller,c.id,key,'assistant','generating',c.source_version,language) returning * into m;
   update public.assistant_conversations set updated_at=statement_timestamp() where id=c.id returning * into c;
   created:=true;
  end if;
 elsif p_operation='finish' then
  select * into m from public.assistant_messages where id=(p_payload->>'message_id')::uuid
   and conversation_id=c.id and user_id=caller and role='assistant' for update;
  if not found then raise exception using errcode='P0001',message='assistant_not_found'; end if;
  if m.status='generating' and m.source_version=c.source_version then
   body:=p_payload->'answer';
   if body is not null and body<>'null'::jsonb then
    if m.schema_version='assistant-closed-v2' and
      body->'choice'->>'response_language' is distinct from m.response_language then
     raise exception using errcode='P0001',message='assistant_conflict'; end if;
    if jsonb_typeof(body)<>'object' or octet_length(body::text)>60000
     or jsonb_typeof(body->'sources') is distinct from 'array'
     or jsonb_array_length(body->'sources')>20 then
     raise exception using errcode='P0001',message='assistant_conflict'; end if;
    for source in select * from jsonb_array_elements(body->'sources') loop
     if not exists(select 1 from public.health_observations h join public.health_observation_revisions v on v.observation_id=h.id
      where h.id=(source->>'observation_id')::uuid and h.user_id=caller and h.deleted_at is null
      and v.revision=(source->>'revision')::integer and v.status='active' and v.fields=source->'fields'
      and h.report_id is not distinct from (source->>'report_id')::uuid
      and h.candidate_id is not distinct from (source->>'candidate_id')::uuid
      and v.review_revision is not distinct from (source->>'review_revision')::integer
      and (h.source_type='manual' or exists(select 1 from public.reports r where r.id=h.report_id and r.user_id=caller and r.status='uploaded'))) then
      raise exception using errcode='P0001',message='assistant_conflict'; end if;
    end loop;
   else body:=null; end if;
   update public.assistant_messages set status=case when body is null then 'failed' else 'ready' end,
    answer=body,error_category=p_payload->>'error_category',provider=p_payload->>'provider',model=p_payload->>'model' where id=m.id;
  end if;
 elsif p_operation not in ('create','get') then
  raise exception using errcode='P0001',message='assistant_conflict';
 end if;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at,q.role desc,q.id),'[]') into items
  from public.assistant_messages q where q.conversation_id=c.id and q.user_id=caller;
 return jsonb_build_object('user_id',caller,'created',created,'message_id',m.id,
  'conversation',to_jsonb(c),'messages',items);
end; $$;
commit;
