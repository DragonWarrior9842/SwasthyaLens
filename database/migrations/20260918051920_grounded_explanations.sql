-- Phase 7: bounded synthetic evaluation; model output never changes source facts.
begin;
create table public.report_explanations (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 report_id uuid not null references public.reports(id) on delete cascade,
 idempotency_key uuid not null,
 status text not null check(status in ('generating','ready','failed','stale')),
 provider text not null check(provider in ('openai','mock-test')),
 model text not null check(model='gpt-5.6-terra'),
 prompt_version text not null check(prompt_version='report-education-v1'),
 schema_version text not null check(schema_version='closed-education-v1'),
 catalog_version text not null check(catalog_version='education-en-v1'),
 fingerprint text not null,
 evidence jsonb not null check(jsonb_typeof(evidence)='array' and jsonb_array_length(evidence)<=20 and octet_length(evidence::text)<=100000),
 output jsonb check(output is null or (jsonb_typeof(output)='object' and octet_length(output::text)<=80000)),
 created_at timestamptz not null default statement_timestamp(),
 expires_at timestamptz not null default statement_timestamp()+interval '30 days',
 deadline_at timestamptz not null default statement_timestamp()+interval '90 seconds',
 finished_at timestamptz,
 error_category text check(error_category in ('timeout','interrupted','invalid','authentication','rate_limit','network','provider_failure','source_changed')),
 input_tokens integer check(input_tokens between 0 and 53000),
 output_tokens integer check(output_tokens between 0 and 4000),
 duration_ms integer check(duration_ms between 0 and 90000),
 unique(user_id,idempotency_key),
 check((status='ready' and output is not null) or (status<>'ready' and output is null))
);
create index explanation_owner_report on public.report_explanations(user_id,report_id,created_at desc,id desc);
create index explanation_report on public.report_explanations(report_id);
create index explanation_expiry on public.report_explanations(expires_at);
create index explanation_active on public.report_explanations(deadline_at) where status='generating';

-- This ledger is never refunded or reset by report deletion, retries or expiry.
create table swasthyalens_private.explanation_budget (
 id boolean primary key default true check(id),
 reserved_cents integer not null default 0 check(reserved_cents between 0 and 500)
);
insert into swasthyalens_private.explanation_budget(id) values(true);
create table swasthyalens_private.explanation_evaluation_reports (
 report_id uuid primary key references public.reports(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 fingerprint text not null,
 expires_at timestamptz not null default statement_timestamp()+interval '24 hours'
);
create index explanation_enrollment_owner on swasthyalens_private.explanation_evaluation_reports(user_id);
create table swasthyalens_private.explanation_attempts (
 id uuid primary key,
 user_id uuid not null references auth.users(id) on delete cascade,
 created_at timestamptz not null default statement_timestamp()
);
create index explanation_attempt_owner_time on swasthyalens_private.explanation_attempts(user_id,created_at);
alter table public.report_explanations enable row level security;
alter table public.report_explanations force row level security;
alter table swasthyalens_private.explanation_budget enable row level security;
alter table swasthyalens_private.explanation_budget force row level security;
alter table swasthyalens_private.explanation_evaluation_reports enable row level security;
alter table swasthyalens_private.explanation_evaluation_reports force row level security;
alter table swasthyalens_private.explanation_attempts enable row level security;
alter table swasthyalens_private.explanation_attempts force row level security;
revoke all on public.report_explanations,swasthyalens_private.explanation_budget,
 swasthyalens_private.explanation_evaluation_reports,swasthyalens_private.explanation_attempts
 from public,anon,authenticated,service_role;
grant select on public.report_explanations to authenticated;
create policy explanation_owner on public.report_explanations for select to authenticated using (
 user_id=(select auth.uid()) and (select swasthyalens_private.session_is_active())
 and expires_at>statement_timestamp()
 and exists(select 1 from public.reports r where r.id=report_id and r.user_id=(select auth.uid()) and r.status='uploaded'));

create function swasthyalens_private.explanation_snapshot(p_report uuid,p_owner uuid) returns jsonb
language sql security invoker set search_path='' as $$
 select coalesce(jsonb_agg(to_jsonb(q) order by q.observation_id),'[]'::jsonb) from (
  select o.id as observation_id,v.revision,o.candidate_id,v.review_revision,o.source_run_id,
   c.run_id as parameter_run_id,o.page_number,o.source_start,o.source_end,v.fields
  from public.health_observations o
  join public.health_observation_revisions v on v.observation_id=o.id and v.status='active'
  join public.report_parameter_candidates c on c.id=o.candidate_id
  join public.report_parameter_runs pr on pr.id=c.run_id and pr.report_id=p_report and pr.status='completed'
  join public.report_parameter_reviews rv on rv.candidate_id=c.id and rv.revision=v.review_revision
  where o.user_id=p_owner and o.report_id=p_report and o.source_type='report' and o.deleted_at is null
   and rv.action in ('confirmed','corrected') and rv.fields=v.fields
   and not exists(select 1 from public.report_parameter_reviews n where n.candidate_id=c.id and n.revision>rv.revision)
  order by o.id limit 21
 ) q;
$$;

-- Atomic invalidation: no stale medical output stays readable through the Data API.
create function swasthyalens_private.explanation_observation_changed() returns trigger
language plpgsql security definer set search_path='' as $$
declare report uuid;
begin
 select o.report_id into report from public.health_observations o where o.id=new.observation_id and o.source_type='report';
 if report is not null then
  update public.report_explanations set status='stale',output=null,evidence='[]'::jsonb,
   error_category='source_changed',finished_at=statement_timestamp()
  where report_id=report and status in ('ready','generating');
  delete from swasthyalens_private.explanation_evaluation_reports where report_id=report;
 end if;
 return new;
end; $$;
create trigger explanation_observation_invalidation after insert or update on public.health_observation_revisions
for each row execute function swasthyalens_private.explanation_observation_changed();
create function swasthyalens_private.explanation_report_deleting() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if new.status='deleting' and old.status is distinct from new.status then
  delete from public.report_explanations where report_id=new.id;
  delete from swasthyalens_private.explanation_evaluation_reports where report_id=new.id;
 end if;
 return new;
end; $$;
create trigger explanation_report_deletion after update of status on public.reports
for each row execute function swasthyalens_private.explanation_report_deleting();

create function swasthyalens_private.explanation_cleanup() returns void
language plpgsql security definer set search_path='' as $$
begin
 delete from public.report_explanations where expires_at<=statement_timestamp();
 delete from swasthyalens_private.explanation_evaluation_reports where expires_at<=statement_timestamp();
 delete from swasthyalens_private.explanation_attempts where created_at<statement_timestamp()-interval '25 hours';
 update public.report_explanations set status='failed',error_category='interrupted',output=null,
  finished_at=statement_timestamp() where status='generating' and deadline_at<=statement_timestamp();
end; $$;

create function swasthyalens_private.explanation_call(p_operation text,p_payload jsonb,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
 report uuid:=(p_payload->>'report_id')::uuid; document public.reports%rowtype;
 snapshot jsonb; digest text; enrolled boolean; record public.report_explanations%rowtype;
 request_key uuid; mode text; reserved integer; total integer; created boolean:=false;
begin
 -- Identical report lock order to source review/publication/deletion.
 select * into document from public.reports r where r.id=report and r.user_id=caller and r.status='uploaded' for update;
 if not found then raise exception using errcode='P0001',message='explanation_not_found'; end if;
 delete from public.report_explanations where report_id=report and expires_at<=statement_timestamp();
 update public.report_explanations set status='failed',error_category='interrupted',output=null,
  finished_at=statement_timestamp() where report_id=report and status='generating' and deadline_at<=statement_timestamp();
 snapshot:=swasthyalens_private.explanation_snapshot(report,caller); digest:=md5(snapshot::text);
 enrolled:=exists(select 1 from swasthyalens_private.explanation_evaluation_reports er
  where er.report_id=report and er.user_id=caller and er.fingerprint=digest and er.expires_at>statement_timestamp());
 if p_operation='enroll_synthetic' then
  -- No public HTTP enrollment route. Only the trusted synthetic fixture runner
  -- supplies its independently constructed file digest and exact evidence snapshot.
  if document.sha256 is distinct from p_payload->>'fixture_sha256'
   or snapshot is distinct from p_payload->'expected_evidence' or jsonb_array_length(snapshot) not between 1 and 20 then
   raise exception using errcode='P0001',message='explanation_evidence'; end if;
  insert into swasthyalens_private.explanation_evaluation_reports(report_id,user_id,fingerprint)
   values(report,caller,digest) on conflict(report_id) do update set fingerprint=excluded.fingerprint,
    expires_at=statement_timestamp()+interval '24 hours';
  enrolled:=true;
 elsif p_operation='request' then
  request_key:=(p_payload->>'idempotency_key')::uuid; mode:=p_payload->>'provider';
  if request_key is null or request_key='00000000-0000-0000-0000-000000000000'::uuid
   or mode is null or mode not in ('openai','mock-test') then
   raise exception using errcode='P0001',message='explanation_conflict'; end if;
  select * into record from public.report_explanations e where e.user_id=caller and e.idempotency_key=request_key;
  if found then
   if record.report_id<>report or record.provider<>mode then raise exception using errcode='P0001',message='explanation_conflict'; end if;
  else
   if not enrolled then raise exception using errcode='P0001',message='explanation_evaluation_only'; end if;
   if jsonb_array_length(snapshot) not between 1 and 20 then raise exception using errcode='P0001',message='explanation_evidence'; end if;
   select * into record from public.report_explanations e where e.report_id=report and e.user_id=caller
    and e.status='ready' and e.fingerprint=digest and e.provider=mode order by e.created_at desc,e.id desc limit 1;
   if not found then
    -- A global lock serializes reservation and concurrency decisions across workers.
    select b.reserved_cents into reserved from swasthyalens_private.explanation_budget b where b.id=true for update;
    if reserved is null then raise exception using errcode='P0001',message='explanation_budget'; end if;
    if exists(select 1 from public.report_explanations e where e.user_id=caller and e.status='generating' and e.deadline_at>statement_timestamp())
     or (select count(*) from public.report_explanations e where e.status='generating' and e.deadline_at>statement_timestamp())>=2
     or (select count(*) from swasthyalens_private.explanation_attempts a where a.user_id=caller and a.created_at>statement_timestamp()-interval '1 minute')>=3
     or (select count(*) from swasthyalens_private.explanation_attempts a where a.user_id=caller and a.created_at>statement_timestamp()-interval '24 hours')>=20 then
     raise exception using errcode='P0001',message='explanation_rate_limit'; end if;
    if mode='openai' then
     if reserved+25>500 then raise exception using errcode='P0001',message='explanation_budget'; end if;
     update swasthyalens_private.explanation_budget set reserved_cents=reserved_cents+25 where id=true;
    end if;
    select count(*) into total from public.report_explanations where report_id=report;
    if total>=20 then
     delete from public.report_explanations where id in (select e.id from public.report_explanations e
      where e.report_id=report and e.status<>'generating' order by e.created_at,e.id limit 1);
    end if;
    insert into public.report_explanations(user_id,report_id,idempotency_key,status,provider,model,
     prompt_version,schema_version,catalog_version,fingerprint,evidence)
    values(caller,report,request_key,'generating',mode,'gpt-5.6-terra','report-education-v1','closed-education-v1','education-en-v1',digest,snapshot)
    returning * into record;
    insert into swasthyalens_private.explanation_attempts(id,user_id) values(record.id,caller);
    created:=true;
   end if;
  end if;
 elsif p_operation='finish' then
  select * into record from public.report_explanations e where e.id=(p_payload->>'id')::uuid and e.report_id=report and e.user_id=caller;
  if not found then raise exception using errcode='P0001',message='explanation_not_found'; end if;
  if record.status='generating' then
   if record.fingerprint<>digest or not enrolled then
    update public.report_explanations set status='stale',output=null,evidence='[]'::jsonb,error_category='source_changed',finished_at=statement_timestamp() where id=record.id;
   elsif p_payload->>'error_category' is not null then
    update public.report_explanations set status='failed',output=null,error_category=p_payload->>'error_category',
     duration_ms=(p_payload->>'duration_ms')::integer,finished_at=statement_timestamp() where id=record.id;
   else
    if p_payload->'output'->>'scope' is distinct from 'educational'
     or jsonb_array_length(p_payload->'output'->'items') is distinct from jsonb_array_length(snapshot) then
     raise exception using errcode='P0001',message='explanation_conflict'; end if;
    update public.report_explanations set status='ready',output=p_payload->'output',error_category=null,
     input_tokens=(p_payload->>'input_tokens')::integer,output_tokens=(p_payload->>'output_tokens')::integer,
     duration_ms=(p_payload->>'duration_ms')::integer,finished_at=statement_timestamp() where id=record.id;
   end if;
   select * into record from public.report_explanations where id=record.id;
  end if;
 elsif p_operation<>'state' then
  raise exception using errcode='P0001',message='explanation_conflict';
 end if;
 if p_operation in ('state','enroll_synthetic') then
  if p_payload->>'id' is not null then
   select * into record from public.report_explanations e where e.id=(p_payload->>'id')::uuid and e.report_id=report and e.user_id=caller;
   if not found then raise exception using errcode='P0001',message='explanation_not_found'; end if;
  else
   select * into record from public.report_explanations e where e.report_id=report and e.user_id=caller order by e.created_at desc,e.id desc limit 1;
  end if;
 end if;
 return jsonb_build_object('user_id',caller,'report_id',report,'evidence',snapshot,'evaluation_enrolled',enrolled,
  'created',created,'reserved_cents',case when created and record.provider='openai' then 25 else 0 end,
  'record',case when record.id is null then null else to_jsonb(record) end);
end; $$;
create function public.explanation_call(p_operation text,p_payload jsonb,p_worker_secret text) returns jsonb
language sql security invoker set search_path='' as $$
 select swasthyalens_private.explanation_call(p_operation,p_payload,p_worker_secret);
$$;
revoke all on function public.explanation_call(text,jsonb,text) from public,anon,authenticated,service_role;
revoke all on function swasthyalens_private.explanation_call(text,jsonb,text),
 swasthyalens_private.explanation_snapshot(uuid,uuid),swasthyalens_private.explanation_cleanup(),
 swasthyalens_private.explanation_observation_changed(),swasthyalens_private.explanation_report_deleting()
 from public,anon,authenticated,service_role;
grant execute on function public.explanation_call(text,jsonb,text),swasthyalens_private.explanation_call(text,jsonb,text) to authenticated;
-- Hourly cleanup physically erases expired content even when accounts are inactive.
create extension if not exists pg_cron;
select cron.schedule('swasthyalens-explanation-retention','17 * * * *','select swasthyalens_private.explanation_cleanup()');
commit;
