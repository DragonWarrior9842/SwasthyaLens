-- Isolated synthetic owners only; rollback restores the temporary worker hash.
begin;
set local statement_timeout='30s';
set local lock_timeout='5s';
create temporary table language_test(label text, owner uuid default gen_random_uuid(), session uuid default gen_random_uuid());
insert into language_test(label) values('A'),('B');
grant select on language_test to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
 select owner,'authenticated','authenticated',owner::text||'@language.invalid',now(),now(),now() from language_test;
insert into auth.sessions(id,user_id,created_at,updated_at)
 select session,owner,now()-interval '5 minutes',now() from language_test;
update swasthyalens_private.processing_key set sha256=encode(extensions.digest(repeat('synthetic',8),'sha256'),'hex');
create function pg_temp.language_assert(ok boolean,label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
select pg_temp.language_assert(has_column_privilege('authenticated','public.user_settings','assistant_language','UPDATE'),'owner column grant');
select pg_temp.language_assert(not has_column_privilege('anon','public.user_settings','assistant_language','UPDATE'),'anonymous grant denied');
set local role authenticated;
do $$
declare a record; b record; result jsonb; previous jsonb; cid uuid; mid uuid; key uuid:=gen_random_uuid(); worker text:=repeat('synthetic',8); body jsonb;
begin
 select * into a from pg_temp.language_test where label='A';
 select * into b from pg_temp.language_test where label='B';
 perform set_config('request.jwt.claims',jsonb_build_object('sub',a.owner,'session_id',a.session,'role','authenticated','is_anonymous',false)::text,true);
 insert into public.user_settings(user_id,preferred_language,assistant_language) values(a.owner,'hi','hinglish') on conflict(user_id) do update set preferred_language='hi',assistant_language='hinglish';
 perform pg_temp.language_assert((select count(*)=1 from public.user_settings),'owner settings only');
 begin update public.user_settings set assistant_language='fr' where user_id=a.owner;
  raise exception 'Unsupported assistant enum accepted'; exception when check_violation then null; end;
 begin update public.user_settings set preferred_language='hinglish' where user_id=a.owner;
  raise exception 'Hinglish interface accepted'; exception when check_violation then null; end;
 begin update public.user_settings set assistant_language=null where user_id=a.owner;
  raise exception 'Null language accepted'; exception when not_null_violation then null; end;
 result:=public.assistant_call('create',jsonb_build_object('idempotency_key',gen_random_uuid()),worker);
 cid:=(result->'conversation'->>'id')::uuid;
 result:=public.assistant_call('request',jsonb_build_object('id',cid,'idempotency_key',key,'content','Synthetic language question'),worker);
 mid:=(result->>'message_id')::uuid;
 perform pg_temp.language_assert((select bool_and(response_language='hinglish' and schema_version='assistant-closed-v2' and prompt_version='assistant-evidence-v2') from public.assistant_messages where conversation_id=cid),'frozen v2 preference');
 body:='{"choice":{"response_language":"hi"},"sources":[],"text":"Synthetic"}';
 begin perform public.assistant_call('finish',jsonb_build_object('id',cid,'message_id',mid,'answer',body,'provider','rules','model','rules-v1'),worker);
  raise exception 'Wrong language accepted'; exception when sqlstate 'P0001' then if sqlerrm<>'assistant_conflict' then raise; end if; end;
 body:=jsonb_set(body,'{choice,response_language}','"hinglish"');
 result:=public.assistant_call('finish',jsonb_build_object('id',cid,'message_id',mid,'answer',body,'provider','rules','model','rules-v1'),worker);
 previous:=result->'messages';
 update public.user_settings set preferred_language='en',assistant_language='hi' where user_id=a.owner;
 result:=public.assistant_call('get',jsonb_build_object('id',cid),worker);
 perform pg_temp.language_assert(result->'messages'=previous,'settings do not rewrite or stale history');
 result:=public.assistant_call('request',jsonb_build_object('id',cid,'idempotency_key',key,'content','Synthetic language question','response_language','en'),worker);
 perform pg_temp.language_assert(result->'messages'=previous and not(result->>'created')::boolean,'replay keeps original language');
 result:=public.assistant_call('request',jsonb_build_object('id',cid,'idempotency_key',gen_random_uuid(),'content','New synthetic question','response_language','en'),worker);
 perform pg_temp.language_assert((select response_language='en' from public.assistant_messages where id=(result->>'message_id')::uuid),'explicit override');
 perform set_config('request.jwt.claims',jsonb_build_object('sub',b.owner,'session_id',b.session,'role','authenticated','is_anonymous',false)::text,true);
 insert into public.user_settings(user_id) values(b.owner) on conflict(user_id) do nothing;
 perform pg_temp.language_assert((select assistant_language='en' and preferred_language='en' from public.user_settings where user_id=b.owner),'independent defaults');
 update public.user_settings set assistant_language='hi' where user_id=a.owner;
 perform pg_temp.language_assert(not found,'cross-owner update denied');
 perform pg_temp.language_assert((select count(*)=0 from public.assistant_messages),'cross-owner messages hidden');
end; $$;
reset role;
delete from auth.sessions where id in(select session from language_test);
set local role authenticated;
select pg_temp.language_assert((select count(*)=0 from public.user_settings),'revoked settings hidden');
reset role;
rollback;
