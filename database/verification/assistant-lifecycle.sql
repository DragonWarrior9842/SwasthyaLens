-- Synthetic owners only. Full rollback restores the temporary processing secret.
begin;
set local statement_timeout='30s';
set local lock_timeout='5s';
create temporary table assistant_test(label text,owner uuid default gen_random_uuid(),
 session uuid default gen_random_uuid(),conversation uuid,message uuid,observation uuid default gen_random_uuid());
insert into assistant_test(label) values('A'),('B');
grant select,update on assistant_test to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
 select owner,'authenticated','authenticated',owner::text||'@assistant.invalid',now(),now(),now() from assistant_test;
insert into auth.sessions(id,user_id,created_at,updated_at)
 select session,owner,now()-interval '5 minutes',now() from assistant_test;
update swasthyalens_private.processing_key set sha256=encode(extensions.digest(repeat('synthetic',8),'sha256'),'hex');
create function pg_temp.assistant_assert(ok boolean,label text) returns void language plpgsql as $$
 begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
set local role authenticated;
do $$
declare a record; result jsonb; replay jsonb; key uuid; worker text:=repeat('synthetic',8);
begin
 for a in select * from pg_temp.assistant_test loop
  perform set_config('request.jwt.claims',jsonb_build_object('sub',a.owner,'session_id',a.session,'role','authenticated','is_anonymous',false)::text,true);
  key:=gen_random_uuid();
  result:=public.assistant_call('create',jsonb_build_object('idempotency_key',key),worker);
  replay:=public.assistant_call('create',jsonb_build_object('idempotency_key',key),worker);
  perform pg_temp.assistant_assert(result->'conversation'->>'id'=replay->'conversation'->>'id','create replay');
  a.conversation:=(result->'conversation'->>'id')::uuid;
  update pg_temp.assistant_test set conversation=a.conversation where owner=a.owner;
  key:=gen_random_uuid();
  result:=public.assistant_call('request',jsonb_build_object('id',a.conversation,'idempotency_key',key,'content','Synthetic weight question'),worker);
  update pg_temp.assistant_test set message=(result->>'message_id')::uuid where owner=a.owner;
  replay:=public.assistant_call('request',jsonb_build_object('id',a.conversation,'idempotency_key',key,'content','Synthetic weight question'),worker);
  perform pg_temp.assistant_assert((result->>'created')::boolean and not (replay->>'created')::boolean,'generation replay');
  perform pg_temp.assistant_assert(jsonb_array_length(replay->'messages')=2,'one message pair');
  begin perform public.assistant_call('request',jsonb_build_object('id',a.conversation,'idempotency_key',gen_random_uuid(),'content','Second pending'),worker);
   raise exception 'Concurrent generation allowed'; exception when sqlstate 'P0001' then
   if sqlerrm<>'assistant_rate_limit' then raise; end if; end;
  begin perform public.assistant_call('request',jsonb_build_object('id',a.conversation,'idempotency_key',key,'content','Changed replay'),worker);
   raise exception 'Changed replay accepted'; exception when sqlstate 'P0001' then
   if sqlerrm<>'assistant_conflict' then raise; end if; end;
 end loop;
 for a in select * from pg_temp.assistant_test loop
  perform set_config('request.jwt.claims',jsonb_build_object('sub',a.owner,'session_id',a.session,'role','authenticated','is_anonymous',false)::text,true);
  perform pg_temp.assistant_assert((select count(*)=1 from public.assistant_conversations),'owned list');
  perform pg_temp.assistant_assert((select count(*)=2 from public.assistant_messages),'owned messages');
  for key in select conversation from pg_temp.assistant_test where owner<>a.owner loop
   begin perform public.assistant_call('get',jsonb_build_object('id',key),worker);
    raise exception 'Foreign read accepted'; exception when sqlstate 'P0001' then if sqlerrm<>'assistant_not_found' then raise; end if; end;
   begin perform public.assistant_call('delete',jsonb_build_object('id',key),worker);
    raise exception 'Foreign deletion accepted'; exception when sqlstate 'P0001' then if sqlerrm<>'assistant_not_found' then raise; end if; end;
   begin perform public.assistant_call('request',jsonb_build_object('id',key,'idempotency_key',gen_random_uuid(),'content','foreign'),worker);
    raise exception 'Foreign send accepted'; exception when sqlstate 'P0001' then if sqlerrm<>'assistant_not_found' then raise; end if; end;
  end loop;
 end loop;
end; $$;
reset role;
-- Active source mutation invalidates an in-flight reply before it can be finished.
insert into public.health_observations(id,user_id,source_type,idempotency_key)
 select observation,owner,'manual',gen_random_uuid() from assistant_test;
insert into public.health_observation_revisions(observation_id,revision,status,fields,measured_at,idempotency_key)
 select observation,1,'active','{"original_label":"Weight","raw_value":"70.250","numeric_value":"70.250","original_unit":"kg","canonical_metric":"weight","value_kind":"numeric"}',now()-interval '1 day',gen_random_uuid() from assistant_test;
select pg_temp.assistant_assert((select count(*)=2 from public.assistant_messages where status='stale' and answer is null),'source change discards pending output');
-- Owner mismatch cannot be inserted even by a privileged application writer.
do $$ declare a record; b record; begin
 select * into a from assistant_test where label='A'; select * into b from assistant_test where label='B';
 begin insert into public.assistant_messages(user_id,conversation_id,idempotency_key,role,status,content,source_version)
 values(a.owner,b.conversation,gen_random_uuid(),'user','received','Synthetic',0);
 raise exception 'Owner-parent mismatch accepted'; exception when foreign_key_violation then null; end;
end; $$;
delete from auth.sessions where id in(select session from assistant_test);
set local role authenticated;
select pg_temp.assistant_assert((select count(*)=0 from public.assistant_messages),'revoked SELECT denied');
do $$ begin
 begin perform public.assistant_call('list','{}',repeat('synthetic',8));
 raise exception 'Revoked RPC accepted'; exception when sqlstate '28000' then null; end;
end; $$;
reset role;
delete from public.assistant_conversations where id in(select conversation from assistant_test);
select pg_temp.assistant_assert((select count(*)=0 from public.assistant_messages where user_id in(select owner from assistant_test)),'conversation cascade');
rollback;
