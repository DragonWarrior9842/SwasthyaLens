-- Phase 5: candidates only. No health observations or upstream edits.
begin;
create table public.report_parameter_runs (
 id uuid primary key default gen_random_uuid(),
 report_id uuid not null references public.reports(id) on delete cascade,
 source_run_id uuid not null references public.report_processing_runs(id) on delete cascade,
 idempotency_key uuid not null,
 attempt integer not null check(attempt between 1 and 3),
 status text not null check(status in ('processing','completed','failed')),
 extractor_version text not null check(length(extractor_version) between 1 and 100),
 rules_version text not null check(length(rules_version) between 1 and 100),
 created_at timestamptz not null default statement_timestamp(),
 finished_at timestamptz,
 deadline_at timestamptz not null default statement_timestamp()+interval '60 seconds',
 error_category text check(error_category in ('interrupted','parser_failure','resource_limit')),
 candidate_count integer check(candidate_count between 0 and 200),
 warnings jsonb not null default '[]' check(jsonb_typeof(warnings)='array' and jsonb_array_length(warnings)<=10),
 unique(report_id,idempotency_key), unique(source_run_id,attempt), unique(id,source_run_id),
 check((status='failed')=(error_category is not null)),
 check((status<>'processing')=(finished_at is not null)),
 check(status<>'completed' or candidate_count is not null)
);
create unique index parameter_one_active on public.report_parameter_runs(report_id) where status='processing';
create table public.report_parameter_candidates (
 id uuid primary key default gen_random_uuid(),
 run_id uuid not null,
 source_run_id uuid not null,
 page_number integer not null,
 ordinal integer not null check(ordinal between 1 and 200),
 content jsonb not null check(jsonb_typeof(content)='object' and octet_length(content::text)<=6000),
 created_at timestamptz not null default statement_timestamp(),
 unique(run_id,ordinal),
 foreign key(run_id,source_run_id) references public.report_parameter_runs(id,source_run_id) on delete cascade,
 foreign key(source_run_id,page_number) references public.report_pages(run_id,page_number) on delete cascade
);
create index parameter_source_page on public.report_parameter_candidates(source_run_id,page_number);
create table public.report_parameter_reviews (
 candidate_id uuid not null references public.report_parameter_candidates(id) on delete cascade,
 revision integer not null check(revision between 1 and 20),
 idempotency_key uuid not null,
 action text not null check(action in ('confirmed','corrected','rejected')),
 fields jsonb not null check(jsonb_typeof(fields)='object' and octet_length(fields::text)<=4000),
 actor_id uuid not null references auth.users(id) on delete cascade,
 created_at timestamptz not null default statement_timestamp(),
 primary key(candidate_id,revision), unique(candidate_id,idempotency_key)
);
create index parameter_review_actor on public.report_parameter_reviews(actor_id);
alter table public.report_parameter_runs enable row level security;
alter table public.report_parameter_runs force row level security;
alter table public.report_parameter_candidates enable row level security;
alter table public.report_parameter_candidates force row level security;
alter table public.report_parameter_reviews enable row level security;
alter table public.report_parameter_reviews force row level security;
revoke all on public.report_parameter_runs,public.report_parameter_candidates,public.report_parameter_reviews from public,anon,authenticated,service_role;
grant select on public.report_parameter_runs,public.report_parameter_candidates,public.report_parameter_reviews to authenticated;
create policy parameter_runs_owner on public.report_parameter_runs for select to authenticated using (
 (select swasthyalens_private.session_is_active()) and exists(select 1 from public.reports r
 where r.id=report_id and r.user_id=(select auth.uid()) and r.status='uploaded'));
create policy parameter_candidates_owner on public.report_parameter_candidates for select to authenticated using (
 (select swasthyalens_private.session_is_active()) and exists(select 1 from public.report_parameter_runs r where r.id=run_id));
create policy parameter_reviews_owner on public.report_parameter_reviews for select to authenticated using (
 (select swasthyalens_private.session_is_active()) and exists(select 1 from public.report_parameter_candidates c where c.id=candidate_id));

create function swasthyalens_private.parameter_history(p_report_id uuid,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret);
begin
 perform 1 from public.reports where id=p_report_id and user_id=caller and status='uploaded' for update;
 if not found then raise exception using errcode='P0001',message='report_not_found'; end if;
 update public.report_parameter_runs set status='failed',error_category='interrupted',finished_at=statement_timestamp()
 where report_id=p_report_id and status='processing' and deadline_at<=statement_timestamp();
 return coalesce((select jsonb_agg(to_jsonb(r) order by created_at desc,id desc) from public.report_parameter_runs r where report_id=p_report_id),'[]'::jsonb);
end; $$;
create function swasthyalens_private.parameter_request(p_report_id uuid,p_source_run_id uuid,p_idempotency_key uuid,
 p_extractor_version text,p_rules_version text,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare run public.report_parameter_runs%rowtype; attempts integer;
begin
 perform swasthyalens_private.parameter_history(p_report_id,p_worker_secret);
 if p_idempotency_key is null or p_idempotency_key='00000000-0000-0000-0000-000000000000'::uuid then
 raise exception using errcode='P0001',message='report_conflict'; end if;
 perform 1 from public.report_processing_runs where id=p_source_run_id and report_id=p_report_id and status='completed';
 if not found then raise exception using errcode='P0001',message='report_not_found'; end if;
 select * into run from public.report_parameter_runs where report_id=p_report_id and idempotency_key=p_idempotency_key;
 if found then
   if run.source_run_id<>p_source_run_id then raise exception using errcode='P0001',message='report_conflict'; end if;
   return jsonb_build_object('created',false,'run',to_jsonb(run));
 end if;
 if exists(select 1 from public.report_parameter_runs where report_id=p_report_id and status='processing') then
 raise exception using errcode='P0001',message='report_conflict'; end if;
 select count(*) into attempts from public.report_parameter_runs where source_run_id=p_source_run_id;
 if attempts>=3 then raise exception using errcode='P0001',message='parameter_limit'; end if;
 insert into public.report_parameter_runs(report_id,source_run_id,idempotency_key,attempt,status,extractor_version,rules_version)
 values(p_report_id,p_source_run_id,p_idempotency_key,attempts+1,'processing',p_extractor_version,p_rules_version) returning * into run;
 return jsonb_build_object('created',true,'run',to_jsonb(run));
end; $$;
create function swasthyalens_private.parameter_finish(p_report_id uuid,p_run_id uuid,p_candidates jsonb,p_warnings jsonb,p_error text,p_worker_secret text)
returns boolean language plpgsql security definer set search_path='' as $$
declare run public.report_parameter_runs%rowtype; candidate jsonb; page jsonb; number integer:=0; start_pos integer; end_pos integer;
begin
 perform swasthyalens_private.parameter_history(p_report_id,p_worker_secret);
 select * into run from public.report_parameter_runs where id=p_run_id and report_id=p_report_id for update;
 if not found or run.status<>'processing' or run.deadline_at<=statement_timestamp() then return false; end if;
 if p_error is not null then
 update public.report_parameter_runs set status='failed',error_category=p_error,finished_at=statement_timestamp() where id=p_run_id;
 return true; end if;
 if jsonb_typeof(p_candidates) is distinct from 'array' or jsonb_array_length(p_candidates)>200 or octet_length(p_candidates::text)>750000 then
 raise exception using errcode='P0001',message='report_conflict'; end if;
 for candidate in select value from jsonb_array_elements(p_candidates) loop
 number:=number+1;
 select content into page from public.report_pages where run_id=run.source_run_id and page_number=(candidate->>'page_number')::integer;
 start_pos:=(candidate->>'source_start')::integer; end_pos:=(candidate->>'source_end')::integer;
 if page is null or start_pos is null or end_pos is null or start_pos<0 or end_pos<=start_pos or end_pos>char_length(page->>'text')
 or substring(page->>'text' from start_pos+1 for end_pos-start_pos) is distinct from candidate->>'source_text'
 or candidate->>'source_method' is distinct from page->>'method'
 or candidate->>'certainty' is distinct from 'needs_review' then
 raise exception using errcode='P0001',message='report_conflict'; end if;
 insert into public.report_parameter_candidates(run_id,source_run_id,page_number,ordinal,content)
 values(p_run_id,run.source_run_id,(candidate->>'page_number')::integer,number,candidate);
 end loop;
 update public.report_parameter_runs set status='completed',candidate_count=number,warnings=p_warnings,finished_at=statement_timestamp() where id=p_run_id;
 return true;
end; $$;
create function swasthyalens_private.parameter_result(p_report_id uuid,p_run_id uuid,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare run public.report_parameter_runs%rowtype; candidates jsonb;
begin
 perform swasthyalens_private.parameter_history(p_report_id,p_worker_secret);
 select * into run from public.report_parameter_runs where report_id=p_report_id and status='completed'
 and (p_run_id is null or id=p_run_id) order by created_at desc,id desc limit 1;
 if not found then raise exception using errcode='P0001',message='report_not_found'; end if;
 select coalesce(jsonb_agg(to_jsonb(c)||jsonb_build_object('reviews',coalesce((select jsonb_agg(to_jsonb(v)) from
 (select * from public.report_parameter_reviews where candidate_id=c.id order by revision desc limit 1) v),'[]'::jsonb)) order by c.ordinal),'[]'::jsonb)
 into candidates from public.report_parameter_candidates c where run_id=run.id;
 return jsonb_build_object('run',to_jsonb(run),'candidates',candidates);
end; $$;
create function swasthyalens_private.parameter_reviews(p_report_id uuid,p_candidate_id uuid,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
begin
 perform swasthyalens_private.parameter_history(p_report_id,p_worker_secret);
 perform 1 from public.report_parameter_candidates c join public.report_parameter_runs r on r.id=c.run_id where c.id=p_candidate_id and r.report_id=p_report_id;
 if not found then raise exception using errcode='P0001',message='report_not_found'; end if;
 return coalesce((select jsonb_agg(to_jsonb(v) order by revision desc) from public.report_parameter_reviews v where candidate_id=p_candidate_id),'[]'::jsonb);
end; $$;
create function swasthyalens_private.parameter_review(p_report_id uuid,p_candidate_id uuid,p_idempotency_key uuid,p_expected_revision integer,p_action text,p_fields jsonb,p_worker_secret text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare caller uuid:=swasthyalens_private.processing_require_worker(p_worker_secret); previous public.report_parameter_reviews%rowtype; machine jsonb; current_revision integer;
begin
 perform swasthyalens_private.parameter_reviews(p_report_id,p_candidate_id,p_worker_secret);
 select * into previous from public.report_parameter_reviews where candidate_id=p_candidate_id and idempotency_key=p_idempotency_key;
 if found then return to_jsonb(previous); end if;
 select * into previous from public.report_parameter_reviews where candidate_id=p_candidate_id order by revision desc limit 1;
 current_revision:=coalesce(previous.revision,0);
 if current_revision<>p_expected_revision or current_revision>=20 then raise exception using errcode='P0001',message='report_conflict'; end if;
 select content->'fields' into machine from public.report_parameter_candidates where id=p_candidate_id;
 if p_action<>'corrected' then p_fields:=coalesce(previous.fields,machine); end if;
 if p_fields is null or p_action is null or p_idempotency_key is null then raise exception using errcode='P0001',message='report_conflict'; end if;
 insert into public.report_parameter_reviews(candidate_id,revision,idempotency_key,action,fields,actor_id)
 values(p_candidate_id,current_revision+1,p_idempotency_key,p_action,p_fields,caller) returning * into previous;
 return to_jsonb(previous);
end; $$;

-- Public invoker wrappers; all mutations require the BFF secret AND owner JWT.
create function public.parameter_history(p_report_id uuid,p_worker_secret text) returns jsonb language sql security invoker set search_path='' as $$ select swasthyalens_private.parameter_history(p_report_id,p_worker_secret); $$;
create function public.parameter_request(p_report_id uuid,p_source_run_id uuid,p_idempotency_key uuid,p_extractor_version text,p_rules_version text,p_worker_secret text) returns jsonb language sql security invoker set search_path='' as $$ select swasthyalens_private.parameter_request(p_report_id,p_source_run_id,p_idempotency_key,p_extractor_version,p_rules_version,p_worker_secret); $$;
create function public.parameter_finish(p_report_id uuid,p_run_id uuid,p_candidates jsonb,p_warnings jsonb,p_error text,p_worker_secret text) returns boolean language sql security invoker set search_path='' as $$ select swasthyalens_private.parameter_finish(p_report_id,p_run_id,p_candidates,p_warnings,p_error,p_worker_secret); $$;
create function public.parameter_result(p_report_id uuid,p_run_id uuid,p_worker_secret text) returns jsonb language sql security invoker set search_path='' as $$ select swasthyalens_private.parameter_result(p_report_id,p_run_id,p_worker_secret); $$;
create function public.parameter_reviews(p_report_id uuid,p_candidate_id uuid,p_worker_secret text) returns jsonb language sql security invoker set search_path='' as $$ select swasthyalens_private.parameter_reviews(p_report_id,p_candidate_id,p_worker_secret); $$;
create function public.parameter_review(p_report_id uuid,p_candidate_id uuid,p_idempotency_key uuid,p_expected_revision integer,p_action text,p_fields jsonb,p_worker_secret text) returns jsonb language sql security invoker set search_path='' as $$ select swasthyalens_private.parameter_review(p_report_id,p_candidate_id,p_idempotency_key,p_expected_revision,p_action,p_fields,p_worker_secret); $$;
do $$ declare f record; begin
 for f in select p.oid::regprocedure as signature from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in ('public','swasthyalens_private') and p.proname in ('parameter_history','parameter_request','parameter_finish','parameter_result','parameter_reviews','parameter_review') loop
 execute format('revoke all on function %s from public,anon,authenticated,service_role',f.signature);
 execute format('grant execute on function %s to authenticated',f.signature);
 end loop;
end; $$;
commit;
