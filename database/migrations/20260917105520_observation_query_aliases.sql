-- Disambiguate PL/pgSQL row variables from SQL relation aliases.
begin;
create or replace function swasthyalens_private.observation_call(p_operation text,p_payload jsonb,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
 o public.health_observations%rowtype; v public.health_observation_revisions%rowtype;
 c public.report_parameter_candidates%rowtype; review public.report_parameter_reviews%rowtype;
 report uuid; key uuid; expected integer; day date; instant timestamptz; latest integer;
 data jsonb; items jsonb; total integer; metric text; source text; from_day date; to_day date;
 offset_rows integer; include_inactive boolean; value_text text; unit_text text;
begin
 if p_operation='publish' then
  report:=(p_payload->>'report_id')::uuid;
  -- Shared with review/deletion: makes latest-revision check + publication atomic.
  perform 1 from public.reports where id=report and user_id=caller and status='uploaded' for update;
  if not found then raise exception using errcode='P0001',message='observation_not_found'; end if;
  select pc.* into c from public.report_parameter_candidates pc join public.report_parameter_runs pr on pr.id=pc.run_id
  where pc.id=(p_payload->>'candidate_id')::uuid and pr.report_id=report and pr.status='completed';
  if not found then raise exception using errcode='P0001',message='observation_not_found'; end if;
  select * into review from public.report_parameter_reviews where candidate_id=c.id order by revision desc limit 1;
  expected:=(p_payload->>'expected_revision')::integer; day:=(p_payload->>'measurement_date')::date;
  if review.revision is null or expected is distinct from review.revision or review.action not in ('confirmed','corrected')
   or nullif(btrim(review.fields->>'raw_value'),'') is null then
   raise exception using errcode='P0001',message='observation_conflict'; end if;
  select * into o from public.health_observations where candidate_id=c.id;
  if not found then
   if exists(select 1 from public.health_observations where report_id=report and source_run_id=c.source_run_id
    and page_number=c.page_number and source_start=(c.content->>'source_start')::integer and source_end=(c.content->>'source_end')::integer) then
    raise exception using errcode='P0001',message='observation_duplicate_source'; end if;
   insert into public.health_observations(user_id,source_type,report_id,candidate_id,source_run_id,page_number,source_start,source_end)
   values(caller,'report',report,c.id,c.source_run_id,c.page_number,(c.content->>'source_start')::integer,(c.content->>'source_end')::integer) returning * into o;
  end if;
  select * into v from public.health_observation_revisions where observation_id=o.id and review_revision=expected;
  if found then
   if v.measurement_date is distinct from day then raise exception using errcode='P0001',message='observation_conflict'; end if;
   return swasthyalens_private.observation_document(o.id,true);
  end if;
  select coalesce(max(revision),0)+1 into latest from public.health_observation_revisions where observation_id=o.id;
  insert into public.health_observation_revisions(observation_id,revision,status,fields,measurement_date,candidate_id,review_revision)
  values(o.id,latest,'active',review.fields,day,c.id,expected);
  return swasthyalens_private.observation_document(o.id,true);
 elsif p_operation in ('manual_create','manual_edit','manual_delete') then
  if p_operation='manual_create' then
   -- Serialize per-account creates without interfering with report lock order.
   perform 1 from auth.users where id=caller for update;
   key:=(p_payload->>'idempotency_key')::uuid;
   if key is null or key='00000000-0000-0000-0000-000000000000'::uuid then
    raise exception using errcode='P0001',message='observation_conflict'; end if;
   select * into o from public.health_observations where user_id=caller and idempotency_key=key;
   if found and o.deleted_at is not null then raise exception using errcode='P0001',message='observation_not_found'; end if;
  else
   select * into o from public.health_observations where id=(p_payload->>'id')::uuid and user_id=caller and source_type='manual' for update;
   if not found then raise exception using errcode='P0001',message='observation_not_found'; end if;
   if o.deleted_at is not null then
    if p_operation='manual_delete' then return jsonb_build_object('message','Observation deleted.'); end if;
    raise exception using errcode='P0001',message='observation_not_found'; end if;
  end if;
  select coalesce(max(revision),0) into latest from public.health_observation_revisions where observation_id=o.id;
  if p_operation='manual_delete' then
   if (p_payload->>'expected_revision')::integer is distinct from latest then
    raise exception using errcode='P0001',message='observation_conflict'; end if;
   delete from public.health_observation_revisions where observation_id=o.id;
   update public.health_observations set deleted_at=statement_timestamp() where id=o.id;
   return jsonb_build_object('message','Observation deleted.');
  end if;
  data:=p_payload->'fields'; value_text:=data->>'raw_value'; unit_text:=data->>'original_unit'; metric:=data->>'canonical_metric';
  instant:=(p_payload->>'measured_at')::timestamptz; key:=(p_payload->>'idempotency_key')::uuid;
  if key is null or key='00000000-0000-0000-0000-000000000000'::uuid or instant is null
   or data->>'value_kind' is distinct from 'numeric' or data->>'numeric_value' is distinct from value_text
   or data->>'comparator' is not null or value_text is null or length(value_text)>12
   or ((metric='weight' and unit_text='kg' and value_text ~ '^[0-9]{1,4}(\.[0-9]{1,3})?$')
       or (metric='heart_rate' and unit_text='bpm' and value_text ~ '^[0-9]{1,4}$')) is distinct from true then
   raise exception using errcode='P0001',message='observation_conflict'; end if;
  if value_text::numeric<=0 or value_text::numeric>=10000 then raise exception using errcode='P0001',message='observation_conflict'; end if;
  if o.id is not null then
   select * into v from public.health_observation_revisions where observation_id=o.id and idempotency_key=key;
   if found then
    if v.fields is distinct from data or v.measured_at is distinct from instant then raise exception using errcode='P0001',message='observation_conflict'; end if;
    return swasthyalens_private.observation_document(o.id,true);
   end if;
   if p_operation='manual_create' or (p_payload->>'expected_revision')::integer is distinct from latest or latest>=100 then
    raise exception using errcode='P0001',message='observation_conflict'; end if;
   update public.health_observation_revisions set status='superseded',status_changed_at=statement_timestamp() where observation_id=o.id and status='active';
  else
   select count(*) into total from public.health_observations where user_id=caller and source_type='manual';
   if total>=1000 then raise exception using errcode='P0001',message='observation_limit'; end if;
   insert into public.health_observations(user_id,source_type,idempotency_key) values(caller,'manual',key) returning * into o;
  end if;
  insert into public.health_observation_revisions(observation_id,revision,status,fields,measured_at,idempotency_key)
  values(o.id,latest+1,'active',data,instant,key);
  return swasthyalens_private.observation_document(o.id,true);
 elsif p_operation='get' then
  select * into o from public.health_observations where id=(p_payload->>'id')::uuid and user_id=caller and deleted_at is null;
  if not found or (o.source_type='report' and not exists(select 1 from public.reports where id=o.report_id and user_id=caller and status='uploaded')) then
   raise exception using errcode='P0001',message='observation_not_found'; end if;
  return swasthyalens_private.observation_document(o.id,true);
 elsif p_operation in ('list','dashboard') then
  metric:=p_payload->>'metric'; source:=p_payload->>'source_type'; report:=(p_payload->>'report_id')::uuid;
  from_day:=(p_payload->>'date_from')::date; to_day:=(p_payload->>'date_to')::date;
  offset_rows:=coalesce((p_payload->>'offset')::integer,0); include_inactive:=coalesce((p_payload->>'include_inactive')::boolean,false);
  if offset_rows<0 or offset_rows>10000 or (source is not null and source not in ('manual','report'))
  or length(metric)>80 or from_day>to_day then raise exception using errcode='P0001',message='observation_conflict'; end if;
  if report is not null and not exists(select 1 from public.reports where id=report and user_id=caller and status='uploaded') then
   raise exception using errcode='P0001',message='observation_not_found'; end if;
  select coalesce(jsonb_agg(swasthyalens_private.observation_document(q.id,false) order by q.day desc nulls last,q.created_at desc,q.id desc),'[]'::jsonb) into items from (
   select h.id,h.created_at,coalesce(latest_row.measurement_date,(latest_row.measured_at at time zone 'UTC')::date) as day
   from public.health_observations h cross join lateral
    (select * from public.health_observation_revisions r where r.observation_id=h.id order by revision desc limit 1) latest_row
   where h.user_id=caller and h.deleted_at is null
    and (h.source_type='manual' or exists(select 1 from public.reports where id=h.report_id and user_id=caller and status='uploaded'))
    and (include_inactive or latest_row.status='active') and (metric is null or latest_row.fields->>'canonical_metric'=metric)
    and (source is null or h.source_type=source) and (report is null or h.report_id=report)
    and (from_day is null or coalesce(latest_row.measurement_date,(latest_row.measured_at at time zone 'UTC')::date)>=from_day)
    and (to_day is null or coalesce(latest_row.measurement_date,(latest_row.measured_at at time zone 'UTC')::date)<=to_day)
   order by day desc nulls last,h.created_at desc,h.id desc limit 21 offset offset_rows
  ) q;
  if p_operation='list' then return jsonb_build_object('items',items,'offset',offset_rows); end if;
  return jsonb_build_object('user_id',caller,
   'uploaded_reports',(select count(*) from public.reports where user_id=caller and status='uploaded'),
   'reviewed_parameters',(select count(*) from public.report_parameter_candidates candidate_row join public.report_parameter_runs r on r.id=candidate_row.run_id
    join public.reports p on p.id=r.report_id cross join lateral
    (select action from public.report_parameter_reviews where candidate_id=candidate_row.id order by revision desc limit 1) rv
    where p.user_id=caller and p.status='uploaded' and rv.action in ('confirmed','corrected')),
   'active_observations',(select count(*) from public.health_observations h join public.health_observation_revisions latest_row on latest_row.observation_id=h.id and latest_row.status='active'
    where h.user_id=caller and h.deleted_at is null and (h.source_type='manual' or exists(select 1 from public.reports where id=h.report_id and user_id=caller and status='uploaded'))),
   'observations',items,
   'reports',coalesce((select jsonb_agg(to_jsonb(q) order by q.created_at desc,q.id desc) from
    (select id,original_filename,created_at from public.reports where user_id=caller and status='uploaded' order by created_at desc,id desc limit 3) q),'[]'::jsonb));
 end if;
 raise exception using errcode='P0001',message='observation_conflict';
end; $$;
commit;
