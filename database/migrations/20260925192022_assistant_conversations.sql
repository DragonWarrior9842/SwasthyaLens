-- Phase 9: two owned tables; evidence is a bounded part of a validated answer.
begin;
create table public.assistant_conversations (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 idempotency_key uuid not null,
 source_version bigint not null default 0,
 created_at timestamptz not null default statement_timestamp(),
 updated_at timestamptz not null default statement_timestamp(),
 unique(user_id,id), unique(user_id,idempotency_key)
);
create index assistant_conversation_owner_recent on public.assistant_conversations(user_id,updated_at desc,id);
create table public.assistant_messages (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null,
 conversation_id uuid not null,
 idempotency_key uuid not null,
 role text not null check(role in ('user','assistant')),
 status text not null check(status in ('received','generating','ready','failed','stale')),
 content text check(length(content) between 1 and 2000),
 answer jsonb check(jsonb_typeof(answer)='object' and octet_length(answer::text)<=60000),
 source_version bigint not null,
 error_category text check(error_category in ('unavailable','invalid_output','timeout','source_changed','interrupted','rate_limit')),
 provider text check(provider in ('gemini','mock-test','rules')),
 model text,
 prompt_version text not null default 'assistant-evidence-v1' check(prompt_version='assistant-evidence-v1'),
 schema_version text not null default 'assistant-closed-v1' check(schema_version='assistant-closed-v1'),
 created_at timestamptz not null default statement_timestamp(),
 foreign key(user_id,conversation_id) references public.assistant_conversations(user_id,id) on delete cascade,
 unique(conversation_id,idempotency_key,role),
 check((role='user' and status='received' and content is not null and answer is null and provider is null and model is null)
  or (role='assistant' and content is null and status<>'received' and
   ((status='ready' and answer is not null) or (status<>'ready' and answer is null)))),
 check((provider is null and model is null) or (provider='gemini' and model='gemini-3.8-flash')
  or (provider='mock-test' and model='deterministic-test') or (provider='rules' and model='rules-v1'))
);
create index assistant_message_owner_parent on public.assistant_messages(user_id,conversation_id,created_at,id);
create index assistant_message_pending on public.assistant_messages(created_at) where status='generating';
alter table public.assistant_conversations enable row level security;
alter table public.assistant_conversations force row level security;
alter table public.assistant_messages enable row level security;
alter table public.assistant_messages force row level security;
revoke all on public.assistant_conversations,public.assistant_messages from public,anon,authenticated,service_role;
grant select on public.assistant_conversations,public.assistant_messages to authenticated;
create policy assistant_conversation_owner on public.assistant_conversations for select to authenticated using
 (user_id=(select auth.uid()) and (select swasthyalens_private.session_is_active()));
create policy assistant_message_owner on public.assistant_messages for select to authenticated using
 (user_id=(select auth.uid()) and (select swasthyalens_private.session_is_active()));

-- Source changes remove answer text/facts/provenance, including in-flight output.
-- Conservative owner-wide invalidation also covers no-data results and new evidence.
create function swasthyalens_private.assistant_source_changed() returns trigger
language plpgsql security definer set search_path='' as $$
declare owner_id uuid; value jsonb;
begin
 value:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
 if tg_table_name='health_observation_revisions' then
  select user_id into owner_id from public.health_observations where id=(value->>'observation_id')::uuid;
 else owner_id:=(value->>'user_id')::uuid; end if;
 if owner_id is not null then
  perform pg_advisory_xact_lock(hashtextextended('assistant-owner:'||owner_id::text,0));
  update public.assistant_conversations set source_version=source_version+1 where user_id=owner_id;
  update public.assistant_messages set status='stale',answer=null,error_category='source_changed'
   where user_id=owner_id and role='assistant' and status in ('ready','generating');
 end if;
 return case when tg_op='DELETE' then old else new end;
end; $$;
revoke all on function swasthyalens_private.assistant_source_changed() from public,anon,authenticated,service_role;
create trigger assistant_observation_changes before update or delete on public.health_observations
 for each row execute function swasthyalens_private.assistant_source_changed();
create trigger assistant_revision_changes after insert or update or delete on public.health_observation_revisions
 for each row execute function swasthyalens_private.assistant_source_changed();
create trigger assistant_report_changes before insert or update or delete on public.reports
 for each row execute function swasthyalens_private.assistant_source_changed();
create trigger assistant_timezone_changes after update of timezone on public.user_settings
 for each row when (old.timezone is distinct from new.timezone)
 execute function swasthyalens_private.assistant_source_changed();

-- Backend-only writes match the established processing-secret + user JWT pattern.
-- Definer is necessary because client table mutations are deliberately not granted.
create function swasthyalens_private.assistant_call(p_operation text,p_payload jsonb,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
 c public.assistant_conversations%rowtype; m public.assistant_messages%rowtype;
 key uuid; created boolean:=false; items jsonb; source jsonb; body jsonb;
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
   insert into public.assistant_messages(user_id,conversation_id,idempotency_key,role,status,content,source_version)
    values(caller,c.id,key,'user','received',p_payload->>'content',c.source_version);
   insert into public.assistant_messages(user_id,conversation_id,idempotency_key,role,status,source_version)
    values(caller,c.id,key,'assistant','generating',c.source_version) returning * into m;
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
create function public.assistant_call(p_operation text,p_payload jsonb,p_worker_secret text) returns jsonb
language sql security invoker set search_path='' as $$
 select swasthyalens_private.assistant_call(p_operation,p_payload,p_worker_secret);
$$;
revoke all on function public.assistant_call(text,jsonb,text),swasthyalens_private.assistant_call(text,jsonb,text) from public,anon,authenticated,service_role;
grant execute on function public.assistant_call(text,jsonb,text),swasthyalens_private.assistant_call(text,jsonb,text) to authenticated;
commit;
