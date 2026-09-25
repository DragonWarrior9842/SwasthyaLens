-- Dedicated disposable SQL fixtures. Everything, including auth rows, rolls back.
begin;
create temp table trend_test(owner uuid default gen_random_uuid(),session uuid default gen_random_uuid(),
 observation uuid default gen_random_uuid(), label text);
insert into trend_test(label) values('A'),('B');
grant select on trend_test to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
 select owner,'authenticated','authenticated',owner::text||'@trends.invalid',now(),now(),now() from trend_test;
insert into auth.sessions(id,user_id,created_at,updated_at)
 select session,owner,now()-interval '5 minutes',now() from trend_test;
insert into public.user_settings(user_id,timezone) select owner,'Asia/Kolkata' from trend_test;
insert into public.health_observations(id,user_id,source_type,idempotency_key)
 select observation,owner,'manual',gen_random_uuid() from trend_test;
insert into public.health_observation_revisions(observation_id,revision,status,fields,measured_at,idempotency_key)
 select observation,1,'active',jsonb_build_object('canonical_metric','weight','original_label','Weight',
 'raw_value',case label when 'A' then '70' else '90' end,'numeric_value',case label when 'A' then '70' else '90' end,
 'value_kind','numeric','original_unit','kg'),timestamptz '2019-12-31T18:30:00Z',gen_random_uuid() from trend_test;
create function pg_temp.trend_check(ok boolean,label text) returns void language plpgsql as $$
 begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
set local role authenticated;
do $$
declare actor record; ctx jsonb;
begin
 for actor in select * from pg_temp.trend_test loop
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,
   'role','authenticated','is_anonymous',false)::text,true);
  ctx:=public.trend_context('weight','kg',7,'2020-01-07');
  perform pg_temp.trend_check(jsonb_array_length(ctx->'items')=1,'exact owner count');
  perform pg_temp.trend_check(ctx->'items'->0->>'id'=actor.observation::text,'own identity only');
  perform pg_temp.trend_check(ctx->>'timezone'='Asia/Kolkata','saved timezone');
  perform pg_temp.trend_check(ctx->>'history_start'='2019-12-25','two exact seven-day windows');
  perform pg_temp.trend_check(public.trend_context('weight','kg',7,'2019-12-31')->'items'='[]','local midnight boundary');
  perform pg_temp.trend_check(public.trend_context('weight','bpm',7,'2020-01-07')->'items'='[]','exact units only');
  perform pg_temp.trend_check(jsonb_array_length(public.trend_context()->'series')=1,'owned catalog only');
  begin perform public.trend_context('weight','kg',90,'2020-01-07');
   raise exception 'Unbounded window accepted'; exception when sqlstate 'P0001' then
   if sqlerrm<>'trend_invalid' then raise; end if; end;
 end loop;
end; $$;
reset role;
-- Supersession removes old active input, rather than counting both revisions.
update public.health_observation_revisions set status='superseded',status_changed_at=now()
 where observation_id in(select observation from trend_test);
insert into public.health_observation_revisions(observation_id,revision,status,fields,measured_at,idempotency_key)
 select observation,2,'active','{"canonical_metric":"weight","original_label":"Weight","raw_value":"71.25","numeric_value":"71.25","value_kind":"numeric","original_unit":"kg"}',
 timestamptz '2020-01-01T12:00:00Z',gen_random_uuid() from trend_test;
set local role authenticated;
do $$
declare actor record; ctx jsonb;
begin
 for actor in select * from pg_temp.trend_test loop
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,
   'role','authenticated','is_anonymous',false)::text,true);
  ctx:=public.trend_context('weight','kg',7,'2020-01-07');
  perform pg_temp.trend_check(jsonb_array_length(ctx->'items')=1 and ctx->'items'->0->'current'->>'revision'='2','only active revision');
 end loop;
end; $$;
reset role;
delete from public.health_observation_revisions where observation_id in(select observation from trend_test);
update public.health_observations set deleted_at=now() where id in(select observation from trend_test);
set local role authenticated;
select pg_temp.trend_check(public.trend_context('weight','kg',7,'2020-01-07')->'items'='[]','deletion reflected');
reset role;
delete from auth.sessions where id in(select session from trend_test);
set local role authenticated;
do $$ begin
 begin perform public.trend_context(); raise exception 'Revoked session accepted';
 exception when sqlstate '28000' then null; end;
end; $$;
reset role;
rollback;
