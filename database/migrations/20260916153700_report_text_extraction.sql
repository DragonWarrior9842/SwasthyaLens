-- Phase 4 only. Original report lifecycle and Storage policies are unchanged.
begin;
create table swasthyalens_private.processing_key (
  singleton boolean primary key default true check (singleton),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$')
);
revoke all on swasthyalens_private.processing_key from public, anon, authenticated, service_role;

create table public.report_processing_runs (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.reports(id) on delete cascade,
  idempotency_key uuid not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  attempt integer not null check (attempt between 1 and 3),
  status text not null check (status in ('queued','processing','completed','failed')),
  created_at timestamptz not null default statement_timestamp(),
  started_at timestamptz,
  finished_at timestamptz,
  deadline_at timestamptz not null default statement_timestamp() + interval '180 seconds',
  error_category text check (error_category in ('corrupt_document','encrypted_document',
    'unsupported_document','page_limit_exceeded','resource_limit_exceeded','extractor_failure',
    'ocr_unavailable','ocr_failure','timeout','interrupted','source_unavailable')),
  processor text check (char_length(processor) <= 500),
  configuration jsonb,
  page_count integer check (page_count between 1 and 20),
  unique(report_id, idempotency_key),
  unique(report_id, attempt),
  check ((status in ('completed','failed')) = (finished_at is not null)),
  check ((status = 'failed') = (error_category is not null)),
  check (status <> 'completed' or (page_count is not null and processor is not null))
);
create unique index report_processing_one_active on public.report_processing_runs(report_id)
  where status in ('queued','processing');

create table public.report_pages (
  run_id uuid not null references public.report_processing_runs(id) on delete cascade,
  page_number integer not null check (page_number between 1 and 20),
  content jsonb not null check (jsonb_typeof(content) = 'object' and octet_length(content::text) <= 750000),
  primary key(run_id, page_number)
);
alter table public.report_processing_runs enable row level security;
alter table public.report_processing_runs force row level security;
alter table public.report_pages enable row level security;
alter table public.report_pages force row level security;
revoke all on public.report_processing_runs, public.report_pages from public, anon, authenticated, service_role;
grant select on public.report_processing_runs, public.report_pages to authenticated;
create policy processing_read_own_active on public.report_processing_runs for select to authenticated
using ((select swasthyalens_private.session_is_active()) and exists
  (select 1 from public.reports r where r.id = report_id and r.user_id = (select auth.uid()) and r.status = 'uploaded'));
create policy pages_read_own_active on public.report_pages for select to authenticated
using ((select swasthyalens_private.session_is_active()) and exists
  (select 1 from public.report_processing_runs p where p.id = run_id));

-- This local server credential prevents ordinary owner JWTs from fabricating
-- machine output. It never replaces the mandatory owner+session checks.
create function swasthyalens_private.processing_require_worker(p_worker_secret text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.report_require_user();
begin
  if p_worker_secret is null or length(p_worker_secret) < 40 or not exists
    (select 1 from swasthyalens_private.processing_key
     where sha256 = encode(extensions.digest(p_worker_secret, 'sha256'), 'hex')) then
    raise exception using errcode = '42501', message = 'processing_worker_required';
  end if;
  return caller;
end;
$$;

create function swasthyalens_private.processing_history(p_report_id uuid, p_worker_secret text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.processing_require_worker(p_worker_secret);
begin
  perform 1 from public.reports where id = p_report_id and user_id = caller and status = 'uploaded' for update;
  if not found then raise exception using errcode='P0001', message='report_not_found'; end if;
  update public.report_processing_runs set status='failed', error_category='interrupted', finished_at=statement_timestamp()
    where report_id=p_report_id and status in ('queued','processing') and deadline_at <= statement_timestamp();
  return coalesce((select jsonb_agg(to_jsonb(p) order by attempt desc)
    from public.report_processing_runs p where report_id=p_report_id), '[]'::jsonb);
end;
$$;

create function swasthyalens_private.processing_request(p_report_id uuid, p_idempotency_key uuid, p_worker_secret text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.processing_require_worker(p_worker_secret);
  document public.reports%rowtype; run public.report_processing_runs%rowtype; attempts integer;
begin
  perform swasthyalens_private.processing_history(p_report_id,p_worker_secret);
  select * into document from public.reports where id=p_report_id and user_id=caller and status='uploaded' for update;
  if not found then raise exception using errcode='P0001', message='report_not_found'; end if;
  if p_idempotency_key is null or p_idempotency_key='00000000-0000-0000-0000-000000000000'::uuid then
    raise exception using errcode='P0001', message='report_conflict'; end if;
  select * into run from public.report_processing_runs where report_id=p_report_id and idempotency_key=p_idempotency_key;
  if found then return to_jsonb(run); end if;
  select * into run from public.report_processing_runs where report_id=p_report_id and status in ('queued','processing');
  if found then return to_jsonb(run); end if;
  select count(*) into attempts from public.report_processing_runs where report_id=p_report_id;
  if attempts >= 3 then raise exception using errcode='P0001', message='processing_limit'; end if;
  insert into public.report_processing_runs(report_id,idempotency_key,source_sha256,attempt,status)
    values(p_report_id,p_idempotency_key,document.sha256,attempts+1,'queued') returning * into run;
  return to_jsonb(run);
end;
$$;

create function swasthyalens_private.processing_start(p_report_id uuid, p_run_id uuid, p_worker_secret text)
returns boolean language plpgsql security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.processing_require_worker(p_worker_secret);
begin
  perform 1 from public.reports where id=p_report_id and user_id=caller and status='uploaded' for update;
  if not found then raise exception using errcode='P0001', message='report_not_found'; end if;
  update public.report_processing_runs set status='processing',started_at=statement_timestamp()
    where id=p_run_id and report_id=p_report_id and status='queued' and deadline_at > statement_timestamp();
  return found;
end;
$$;

create function swasthyalens_private.processing_finish(p_report_id uuid, p_run_id uuid,
  p_result jsonb, p_error text, p_worker_secret text)
returns boolean language plpgsql security definer set search_path = '' as $$
declare caller uuid := swasthyalens_private.processing_require_worker(p_worker_secret);
  document public.reports%rowtype; run public.report_processing_runs%rowtype;
  page jsonb; number integer := 0;
begin
  select * into document from public.reports where id=p_report_id and user_id=caller and status='uploaded' for update;
  if not found then raise exception using errcode='P0001', message='report_not_found'; end if;
  select * into run from public.report_processing_runs where id=p_run_id and report_id=p_report_id for update;
  if not found or run.status <> 'processing' or run.deadline_at <= statement_timestamp()
    or run.source_sha256 <> document.sha256 then return false; end if;
  if p_error is not null then
    update public.report_processing_runs set status='failed', error_category=p_error,
      finished_at=statement_timestamp() where id=p_run_id;
    return true;
  end if;
  if p_result is null or octet_length(p_result::text)>900000
    or jsonb_typeof(p_result->'pages') is distinct from 'array'
    or jsonb_array_length(p_result->'pages') not between 1 and 20 then
    raise exception using errcode='P0001', message='report_conflict'; end if;
  for page in select value from jsonb_array_elements(p_result->'pages') loop
    number := number+1;
    if (page->>'page_number')::integer is distinct from number
      or page->>'method' not in ('native_text','ocr')
      or jsonb_typeof(page->'text') is distinct from 'string'
      or char_length(page->>'text')>20000 then
      raise exception using errcode='P0001', message='report_conflict'; end if;
    insert into public.report_pages(run_id,page_number,content) values(p_run_id,number,page);
  end loop;
  update public.report_processing_runs set status='completed',page_count=number,
    processor=p_result->>'processor',configuration=p_result->'configuration',finished_at=statement_timestamp()
    where id=p_run_id;
  return true;
end;
$$;

-- Phase 3 uses tombstones, so FK cascade alone is insufficient. Erase derived
-- data atomically with deletion intent; the report lock fences late completions.
create function swasthyalens_private.erase_report_extraction()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.status in ('deleting','deleted') then
    delete from public.report_processing_runs where report_id=new.id;
  end if;
  return new;
end;
$$;
create trigger report_erase_extraction after update of status on public.reports
for each row execute function swasthyalens_private.erase_report_extraction();

create function public.processing_history(p_report_id uuid, p_worker_secret text)
returns jsonb language sql security invoker set search_path='' as $$
  select swasthyalens_private.processing_history(p_report_id,p_worker_secret); $$;
create function public.processing_request(p_report_id uuid,p_idempotency_key uuid,p_worker_secret text)
returns jsonb language sql security invoker set search_path='' as $$
  select swasthyalens_private.processing_request(p_report_id,p_idempotency_key,p_worker_secret); $$;
create function public.processing_start(p_report_id uuid,p_run_id uuid,p_worker_secret text)
returns boolean language sql security invoker set search_path='' as $$
  select swasthyalens_private.processing_start(p_report_id,p_run_id,p_worker_secret); $$;
create function public.processing_finish(p_report_id uuid,p_run_id uuid,p_result jsonb,p_error text,p_worker_secret text)
returns boolean language sql security invoker set search_path='' as $$
  select swasthyalens_private.processing_finish(p_report_id,p_run_id,p_result,p_error,p_worker_secret); $$;

revoke all on function swasthyalens_private.processing_require_worker(text),
  swasthyalens_private.erase_report_extraction() from public,anon,authenticated,service_role;
revoke all on function swasthyalens_private.processing_history(uuid,text),
  swasthyalens_private.processing_request(uuid,uuid,text), swasthyalens_private.processing_start(uuid,uuid,text),
  swasthyalens_private.processing_finish(uuid,uuid,jsonb,text,text),
  public.processing_history(uuid,text), public.processing_request(uuid,uuid,text),
  public.processing_start(uuid,uuid,text), public.processing_finish(uuid,uuid,jsonb,text,text)
  from public,anon,authenticated,service_role;
grant execute on function swasthyalens_private.processing_history(uuid,text),
  swasthyalens_private.processing_request(uuid,uuid,text), swasthyalens_private.processing_start(uuid,uuid,text),
  swasthyalens_private.processing_finish(uuid,uuid,jsonb,text,text),
  public.processing_history(uuid,text), public.processing_request(uuid,uuid,text),
  public.processing_start(uuid,uuid,text), public.processing_finish(uuid,uuid,jsonb,text,text)
  to authenticated;
commit;
