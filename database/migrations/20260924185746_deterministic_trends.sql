-- Phase 8 reads only active Phase 6 snapshots. No derived persistence or AI.
begin;
create index observation_metric_day_active on public.health_observation_revisions
 ((fields->>'canonical_metric'),(fields->>'original_unit'),measurement_date,observation_id)
 where status='active' and measurement_date is not null;
create index observation_metric_instant_active on public.health_observation_revisions
 ((fields->>'canonical_metric'),(fields->>'original_unit'),measured_at,observation_id)
 where status='active' and measured_at is not null;

create function swasthyalens_private.trend_context(p_metric text default null,
 p_unit text default null,p_window integer default 7,p_end date default null)
returns jsonb language plpgsql stable security invoker set search_path='' as $$
declare caller uuid:=auth.uid(); zone text; captured timestamptz:=statement_timestamp();
 today date; finish date; first_day date; first_instant timestamptz; end_instant timestamptz;
 items jsonb; unknown_count bigint;
begin
 if caller is null or not swasthyalens_private.session_is_active() then
  raise exception using errcode='28000',message='inactive_session'; end if;
 select timezone into zone from public.user_settings where user_id=caller;
 if zone is null then raise exception using errcode='P0001',message='trend_unavailable'; end if;
 today:=(captured at time zone zone)::date; finish:=coalesce(p_end,today);
 if p_window is null or p_window not in (7,30) or finish>today or finish<date '1901-01-01'
  or finish>date '2100-12-31' then
  raise exception using errcode='P0001',message='trend_invalid'; end if;
 if p_metric is null then
  if p_unit is not null then raise exception using errcode='P0001',message='trend_invalid'; end if;
  select coalesce(jsonb_agg(to_jsonb(q) order by q.metric,q.unit nulls last),'[]') into items from (
   select v.fields->>'canonical_metric' as metric,v.fields->>'original_unit' as unit,count(*) as observation_count
   from public.health_observations h join public.health_observation_revisions v on v.observation_id=h.id
   where h.user_id=caller and h.deleted_at is null and v.status='active'
    and v.fields->>'canonical_metric' in ('weight','heart_rate','hemoglobin','tsh','vitamin_d_unspecified','glucose_unspecified','crp')
   group by v.fields->>'canonical_metric',v.fields->>'original_unit'
   order by metric,unit nulls last limit 51
  ) q;
  return jsonb_build_object('user_id',caller,'timezone',zone,'as_of',captured,'period_end',finish,'series',items);
 end if;
 if p_metric not in ('weight','heart_rate','hemoglobin','tsh','vitamin_d_unspecified','glucose_unspecified','crp')
  or p_unit is null or length(p_unit) not between 1 and 60 then
  raise exception using errcode='P0001',message='trend_invalid'; end if;
 first_day:=finish-case when p_metric in ('weight','heart_rate') then 2*p_window-1 else 365 end;
 first_instant:=first_day::timestamp at time zone zone;
 end_instant:=least((finish+1)::timestamp at time zone zone,captured);
 -- Both branches retain indexable native date/instant predicates. RLS also checks
 -- owner, active session and uploaded report state; no candidate text is selected.
 select coalesce(jsonb_agg(q.document order by q.day,q.instant nulls last,q.id),'[]') into items from (
  select h.id,coalesce(v.measurement_date,(v.measured_at at time zone zone)::date) as day,
   v.measured_at as instant,
   jsonb_build_object('id',h.id,'user_id',h.user_id,'source_type',h.source_type,
    'report_id',h.report_id,'candidate_id',h.candidate_id,'created_at',h.created_at,
    'current',to_jsonb(v),'revisions','[]'::jsonb,'evidence',null) as document
  from public.health_observations h join public.health_observation_revisions v on v.observation_id=h.id
  where h.user_id=caller and h.deleted_at is null and v.status='active'
   and v.fields->>'canonical_metric'=p_metric and v.fields->>'original_unit'=p_unit
   and ((v.measurement_date>=first_day and v.measurement_date<=finish)
    or (v.measured_at>=first_instant and v.measured_at<end_instant))
  order by day,instant nulls last,h.id limit 501
 ) q;
 select count(*) into unknown_count from public.health_observations h
 join public.health_observation_revisions v on v.observation_id=h.id
 where h.user_id=caller and h.deleted_at is null and v.status='active'
  and v.fields->>'canonical_metric'=p_metric and v.fields->>'original_unit'=p_unit
  and v.measurement_date is null and v.measured_at is null;
 return jsonb_build_object('user_id',caller,'timezone',zone,'as_of',captured,
  'period_end',finish,'history_start',first_day,'unknown_date_count',unknown_count,'items',items);
end; $$;
create function public.trend_context(p_metric text default null,p_unit text default null,
 p_window integer default 7,p_end date default null) returns jsonb
language sql stable security invoker set search_path='' as $$
 select swasthyalens_private.trend_context(p_metric,p_unit,p_window,p_end);
$$;
revoke all on function public.trend_context(text,text,integer,date),
 swasthyalens_private.trend_context(text,text,integer,date) from public,anon,authenticated,service_role;
grant execute on function public.trend_context(text,text,integer,date),
 swasthyalens_private.trend_context(text,text,integer,date) to authenticated;
commit;
