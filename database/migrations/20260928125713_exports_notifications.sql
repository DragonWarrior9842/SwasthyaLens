-- Phase 11: bounded direct export reads and generic operational notices.
begin;
alter table public.user_settings add column in_app_notifications boolean not null default true;
grant insert(in_app_notifications),update(in_app_notifications) on public.user_settings to authenticated;

create function swasthyalens_private.export_context(p_from date,p_to date,
 p_unknown boolean,p_source text default null,p_report uuid default null)
returns jsonb language plpgsql stable security invoker set search_path='' as $$
declare caller uuid:=swasthyalens_private.report_require_user(); items jsonb;
begin
 if p_from is null or p_to is null or p_unknown is null or p_from>p_to
 or p_to-p_from>365 or p_from<date '1900-01-01' or p_to>date '2100-12-31'
 or (p_source is not null and p_source not in ('report','manual'))
 or (p_report is not null and p_source='manual') then
  raise exception using errcode='P0001',message='export_invalid'; end if;
 if p_report is not null and not exists(select 1 from public.reports
  where id=p_report and user_id=caller and status='uploaded') then
  raise exception using errcode='P0001',message='report_not_found'; end if;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.measurement_date nulls last,q.measured_at nulls last,q.id),'[]')
 into items from (
  select o.id,o.user_id,o.source_type,o.report_id,v.revision,v.status,v.fields,
   v.measurement_date,v.measured_at,v.review_revision,rv.action as review_action,
   r.original_filename as report_name,r.created_at as report_recorded_at,
   c.page_number,c.content->>'source_method' as source_method
  from public.health_observations o
  join public.health_observation_revisions v on v.observation_id=o.id and v.status='active'
  left join public.reports r on r.id=o.report_id and r.user_id=caller and r.status='uploaded'
  left join public.report_parameter_candidates c on c.id=o.candidate_id
  left join public.report_parameter_reviews rv on rv.candidate_id=v.candidate_id and rv.revision=v.review_revision
  where o.user_id=caller and o.deleted_at is null
   and (p_source is null or o.source_type=p_source) and (p_report is null or o.report_id=p_report)
   and (o.source_type='manual' or (r.id is not null and rv.action in ('confirmed','corrected')
    and rv.fields=v.fields and not exists(select 1 from public.report_parameter_reviews newer
     where newer.candidate_id=rv.candidate_id and newer.revision>rv.revision)))
   and ((v.measurement_date between p_from and p_to)
    or (v.measured_at>=p_from::timestamp at time zone 'UTC'
     and v.measured_at<(p_to+1)::timestamp at time zone 'UTC')
    or (p_unknown and v.measurement_date is null and v.measured_at is null))
  order by v.measurement_date nulls last,v.measured_at nulls last,o.id limit 201
 ) q;
 if jsonb_array_length(items)>200 or (select count(distinct value->>'report_id')
  from jsonb_array_elements(items))>20 then
  raise exception using errcode='P0001',message='export_capacity'; end if;
 return jsonb_build_object('user_id',caller,'as_of',statement_timestamp(),'items',items);
end; $$;
create function public.export_context(p_from date,p_to date,p_unknown boolean,
 p_source text default null,p_report uuid default null) returns jsonb
language sql stable security invoker set search_path='' as $$
 select swasthyalens_private.export_context(p_from,p_to,p_unknown,p_source,p_report);
$$;
revoke all on function public.export_context(date,date,boolean,text,uuid),
 swasthyalens_private.export_context(date,date,boolean,text,uuid) from public,anon,authenticated,service_role;
grant execute on function public.export_context(date,date,boolean,text,uuid),
 swasthyalens_private.export_context(date,date,boolean,text,uuid) to authenticated;

create table public.notifications (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 report_id uuid not null references public.reports(id) on delete cascade,
 event_type text not null check(event_type in ('upload_completed','extraction_completed',
  'extraction_failed','parameters_ready','parameters_failed')),
 event_key uuid not null,
 created_at timestamptz not null default statement_timestamp(),
 read_at timestamptz check(read_at>=created_at),
 unique(event_type,event_key)
);
create index notifications_owner_history on public.notifications(user_id,created_at desc,id desc);
create index notifications_report on public.notifications(report_id);
create index notifications_expiration on public.notifications(created_at);
alter table public.notifications enable row level security;
alter table public.notifications force row level security;
revoke all on public.notifications from public,anon,authenticated,service_role;
grant select on public.notifications to authenticated;
create policy notifications_owner on public.notifications for select to authenticated using (
 user_id=(select auth.uid()) and (select swasthyalens_private.session_is_active())
 and created_at>statement_timestamp()-interval '30 days'
 and exists(select 1 from public.reports r where r.id=report_id and r.user_id=(select auth.uid()) and r.status='uploaded'));

-- Only called by lifecycle triggers. No exposed caller can fabricate events.
create function swasthyalens_private.notification_event() returns trigger
language plpgsql security definer set search_path='' as $$
declare owner_id uuid; report uuid; kind text;
begin
 if new.status is not distinct from old.status then return new; end if;
 if tg_table_name='reports' then
  if new.status in ('deleting','deleted') then
   delete from public.notifications where report_id=new.id;
   return new;
  end if;
  if new.status<>'uploaded' then return new; end if;
  report:=new.id; owner_id:=new.user_id; kind:='upload_completed';
 else
  if new.status not in ('completed','failed') then return new; end if;
  report:=new.report_id;
  select user_id into owner_id from public.reports where id=report and status='uploaded';
  if owner_id is null then return new; end if;
  if tg_table_name='report_processing_runs' then
   kind:=case when new.status='completed' then 'extraction_completed' else 'extraction_failed' end;
  else
   if new.status='completed' and new.candidate_count=0 then return new; end if;
   kind:=case when new.status='completed' then 'parameters_ready' else 'parameters_failed' end;
  end if;
 end if;
 if not coalesce((select in_app_notifications from public.user_settings where user_id=owner_id),true)
 then return new; end if;
 perform pg_advisory_xact_lock(hashtextextended('notifications-owner:'||owner_id::text,0));
 insert into public.notifications(user_id,report_id,event_type,event_key)
 values(owner_id,report,kind,new.id) on conflict(event_type,event_key) do nothing;
 delete from public.notifications where user_id=owner_id and
 (created_at<=statement_timestamp()-interval '30 days' or id in
  (select id from public.notifications where user_id=owner_id order by created_at desc,id desc offset 100));
 return new;
end; $$;
revoke all on function swasthyalens_private.notification_event() from public,anon,authenticated,service_role;
create trigger notification_report_transition after update of status on public.reports
 for each row execute function swasthyalens_private.notification_event();
create trigger notification_extraction_transition after update of status on public.report_processing_runs
 for each row execute function swasthyalens_private.notification_event();
create trigger notification_parameter_transition after update of status on public.report_parameter_runs
 for each row execute function swasthyalens_private.notification_event();

create function swasthyalens_private.notification_call(p_operation text,p_id uuid,
 p_offset integer,p_worker_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
 items jsonb; unread integer;
begin
 if p_operation is null or p_operation not in ('list','read','read_all','delete')
 or p_offset is null or p_offset<0 or p_offset>100
 or ((p_operation in ('read','delete'))<>(p_id is not null)) then
  raise exception using errcode='P0001',message='notification_invalid'; end if;
 perform pg_advisory_xact_lock(hashtextextended('notifications-owner:'||caller::text,0));
 delete from public.notifications where user_id=caller and
 (created_at<=statement_timestamp()-interval '30 days' or not exists
  (select 1 from public.reports r where r.id=report_id and r.user_id=caller and r.status='uploaded'));
 if p_operation in ('read','delete') then
  perform 1 from public.notifications where id=p_id and user_id=caller;
  if not found then raise exception using errcode='P0001',message='notification_not_found'; end if;
 end if;
 if p_operation='delete' then delete from public.notifications where id=p_id and user_id=caller;
 elsif p_operation in ('read','read_all') then
  update public.notifications set read_at=greatest(created_at,statement_timestamp())
  where user_id=caller and read_at is null and (p_operation='read_all' or id=p_id);
 end if;
 select count(*) into unread from public.notifications where user_id=caller and read_at is null;
 select coalesce(jsonb_agg(to_jsonb(q) order by q.created_at desc,q.id desc),'[]') into items from
 (select id,user_id,report_id,event_type,created_at,read_at from public.notifications
  where user_id=caller order by created_at desc,id desc limit 21 offset p_offset) q;
 return jsonb_build_object('user_id',caller,'items',items,'unread_count',unread,'offset',p_offset);
end; $$;
create function public.notification_call(p_operation text,p_id uuid,p_offset integer,p_worker_secret text)
returns jsonb language sql security invoker set search_path='' as $$
 select swasthyalens_private.notification_call(p_operation,p_id,p_offset,p_worker_secret);
$$;
revoke all on function public.notification_call(text,uuid,integer,text),
 swasthyalens_private.notification_call(text,uuid,integer,text) from public,anon,authenticated,service_role;
grant execute on function public.notification_call(text,uuid,integer,text),
 swasthyalens_private.notification_call(text,uuid,integer,text) to authenticated;

create function swasthyalens_private.notification_cleanup() returns void
language sql security definer set search_path='' as $$
 delete from public.notifications where created_at<=statement_timestamp()-interval '30 days';
$$;
revoke all on function swasthyalens_private.notification_cleanup() from public,anon,authenticated,service_role;
select cron.schedule('swasthyalens-notification-retention','27 * * * *',
 'select swasthyalens_private.notification_cleanup()');
notify pgrst,'reload schema';
commit;
