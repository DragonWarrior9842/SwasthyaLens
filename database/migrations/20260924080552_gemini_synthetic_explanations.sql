-- Gemini is a synthetic Free Tier evaluation choice only. Preserve the paid ledger.
begin;
alter table public.report_explanations
 drop constraint report_explanations_provider_check,
 drop constraint report_explanations_model_check,
 add constraint explanation_provider_model_check check (
  (provider in ('openai','mock-test') and model='gpt-5.6-terra') or
  (provider='gemini' and model='gemini-3.8-flash'));
-- Permanent and never refunded, including errors, source changes and deletions.
-- Existing forced RLS and absence of client write privileges apply to this column.
alter table swasthyalens_private.explanation_budget
 add column gemini_attempts integer not null default 0 check(gemini_attempts between 0 and 20);
create or replace function swasthyalens_private.explanation_call(p_operation text,p_payload jsonb,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
 report uuid:=(p_payload->>'report_id')::uuid; document public.reports%rowtype;
 snapshot jsonb; digest text; enrolled boolean; record public.report_explanations%rowtype;
 request_key uuid; mode text; reserved integer; attempts integer; total integer; created boolean:=false;
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
   or mode is null or mode not in ('openai','mock-test','gemini') then
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
    select b.reserved_cents,b.gemini_attempts into reserved,attempts from swasthyalens_private.explanation_budget b where b.id=true for update;
    if reserved is null then raise exception using errcode='P0001',message='explanation_budget'; end if;
    if exists(select 1 from public.report_explanations e where e.user_id=caller and e.status='generating' and e.deadline_at>statement_timestamp())
     or (select count(*) from public.report_explanations e where e.status='generating' and e.deadline_at>statement_timestamp())>=2
     or (select count(*) from swasthyalens_private.explanation_attempts a where a.user_id=caller and a.created_at>statement_timestamp()-interval '1 minute')>=3
     or (select count(*) from swasthyalens_private.explanation_attempts a where a.user_id=caller and a.created_at>statement_timestamp()-interval '24 hours')>=20 then
     raise exception using errcode='P0001',message='explanation_rate_limit'; end if;
    if mode='openai' then
     if reserved+25>500 then raise exception using errcode='P0001',message='explanation_budget'; end if;
     update swasthyalens_private.explanation_budget set reserved_cents=reserved_cents+25 where id=true;
    elsif mode='gemini' then
     if attempts is null or attempts>=20 then raise exception using errcode='P0001',message='explanation_budget'; end if;
     update swasthyalens_private.explanation_budget set gemini_attempts=gemini_attempts+1 where id=true returning gemini_attempts into attempts;
    end if;
    select count(*) into total from public.report_explanations where report_id=report;
    if total>=20 then
     delete from public.report_explanations where id in (select e.id from public.report_explanations e
      where e.report_id=report and e.status<>'generating' order by e.created_at,e.id limit 1);
    end if;
    insert into public.report_explanations(user_id,report_id,idempotency_key,status,provider,model,
     prompt_version,schema_version,catalog_version,fingerprint,evidence)
    values(caller,report,request_key,'generating',mode,case when mode='gemini' then 'gemini-3.8-flash' else 'gpt-5.6-terra' end,'report-education-v1','closed-education-v1','education-en-v1',digest,snapshot)
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
  'evaluation_attempt',case when created and record.provider='gemini' then attempts else 0 end,
  'record',case when record.id is null then null else to_jsonb(record) end);
end; $$;

commit;
