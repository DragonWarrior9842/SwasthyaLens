-- Development-only, complete rollback transaction. No Storage objects or real users change.
begin;
set local statement_timeout='30s';
set local lock_timeout='5s';
create temporary table parameter_test_context(label text primary key, owner uuid default gen_random_uuid(),
 session uuid default gen_random_uuid(), report uuid default gen_random_uuid(), source uuid default gen_random_uuid(), run uuid, candidate uuid, second uuid) on commit drop;
insert into parameter_test_context(label) values('A'),('B');
grant select,update on parameter_test_context to authenticated;
insert into auth.users(id,aud,role,email,email_confirmed_at,created_at,updated_at)
select owner,'authenticated','authenticated',owner::text||'@phase5.invalid',now(),now(),now() from parameter_test_context;
insert into auth.sessions(id,user_id,created_at,updated_at)
select session,owner,now()-interval '5 minutes',now() from parameter_test_context;
insert into public.reports(id,user_id,idempotency_key,storage_path,original_filename,media_type,size_bytes,sha256,status)
select report,owner,gen_random_uuid(),owner::text||'/'||report::text||'/'||gen_random_uuid()::text||'.pdf',
 'synthetic.pdf','application/pdf',100,repeat('a',64),'uploaded' from parameter_test_context;
insert into public.report_processing_runs(id,report_id,idempotency_key,source_sha256,attempt,status,finished_at,processor,page_count)
select source,report,gen_random_uuid(),repeat('a',64),1,'completed',now(),'synthetic',1 from parameter_test_context;
insert into public.report_pages(run_id,page_number,content)
select source,1,'{"text":"Test | Result\nSynthetic | 5","method":"native_text"}' from parameter_test_context;
update swasthyalens_private.processing_key set sha256=encode(extensions.digest(repeat('synthetic',8),'sha256'),'hex');
create function pg_temp.check_parameter(ok boolean,label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %',label; end if; end; $$;
create function pg_temp.deny_parameter(statement text,expected text) returns void language plpgsql as $$
begin
 begin execute statement;
 exception when others then if sqlstate=expected then return; end if;
 raise exception 'Unexpected SQLSTATE %, expected %',sqlstate,expected; end;
 raise exception 'Expected denial did not occur';
end; $$;
set local role authenticated;
do $$
declare actor record; other_actor record; result jsonb; replay jsonb; key uuid; worker text:=repeat('synthetic',8);
 payload jsonb:='[{"page_number":1,"source_text":"Synthetic | 5","source_start":14,"source_end":27,"source_method":"native_text","certainty":"needs_review","fields":{"original_label":"Synthetic","raw_value":"5"}}]';
 revision jsonb;
begin
 for actor in select * from pg_temp.parameter_test_context order by label loop
  select * into other_actor from pg_temp.parameter_test_context where label<>actor.label;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
  key:=gen_random_uuid();
  result:=public.parameter_request(actor.report,actor.source,key,'v1','aliases-v1',worker);
  replay:=public.parameter_request(actor.report,actor.source,key,'v2','aliases-v2',worker);
  perform pg_temp.check_parameter(result->>'created'='true' and replay->>'created'='false' and result->'run'->>'id'=replay->'run'->>'id','idempotent claim retains version');
  perform pg_temp.deny_parameter(format('select public.parameter_request(%L,%L,gen_random_uuid(),''v1'',''v1'',%L)',actor.report,actor.source,worker),'P0001');
  update pg_temp.parameter_test_context set run=(result->'run'->>'id')::uuid where label=actor.label;
  perform pg_temp.deny_parameter(format('select public.parameter_finish(%L,%L,%L::jsonb,''[]'',null,%L)',actor.report,result->'run'->>'id',replace(payload::text,'Synthetic | 5','forged source'),worker),'P0001');
  perform pg_temp.check_parameter(public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker),'source-grounded commit');
  perform pg_temp.check_parameter(not public.parameter_finish(actor.report,(result->'run'->>'id')::uuid,payload,'[]',null,worker),'completed attempt immutable');
  select id into actor.candidate from public.report_parameter_candidates where run_id=(result->'run'->>'id')::uuid;
  update pg_temp.parameter_test_context set candidate=actor.candidate where label=actor.label;
  key:=gen_random_uuid();
  revision:=public.parameter_review(actor.report,actor.candidate,key,0,'corrected','{"original_label":"Synthetic","raw_value":"5.00"}',worker);
  replay:=public.parameter_review(actor.report,actor.candidate,key,0,'corrected','{"raw_value":"bad"}',worker);
  perform pg_temp.check_parameter(replay=revision,'review replay immutable');
  perform pg_temp.check_parameter((select content->'fields'->>'raw_value' from public.report_parameter_candidates where id=actor.candidate)='5','correction preserves machine value');
  for n in 1..19 loop
   revision:=public.parameter_review(actor.report,actor.candidate,gen_random_uuid(),n,'confirmed',null,worker);
  end loop;
  perform pg_temp.check_parameter(revision->>'revision'='20' and revision->'fields'->>'raw_value'='5.00','confirmation retains correction');
  perform pg_temp.deny_parameter(format('select public.parameter_review(%L,%L,gen_random_uuid(),20,''confirmed'',null,%L)',actor.report,actor.candidate,worker),'P0001');
  perform pg_temp.check_parameter((select count(*) from public.report_parameter_candidates)=1,'owner-only candidate RLS');
  perform pg_temp.check_parameter((select count(*) from public.report_parameter_reviews)=20,'owner-only review RLS');
  perform pg_temp.deny_parameter('update public.report_parameter_candidates set content=''{}''','42501');
  perform pg_temp.deny_parameter('delete from public.report_parameter_reviews','42501');
  perform pg_temp.deny_parameter(format('select public.parameter_result(%L,null,%L)',other_actor.report,worker),'P0001');
  perform pg_temp.deny_parameter(format('select public.parameter_request(%L,%L,gen_random_uuid(),''v1'',''v1'',%L)',actor.report,other_actor.source,worker),'P0001');
  result:=public.parameter_request(actor.report,actor.source,gen_random_uuid(),'v2','aliases-v2',worker);
  update pg_temp.parameter_test_context set second=(result->'run'->>'id')::uuid where label=actor.label;
 end loop;
end; $$;
reset role;
update public.report_parameter_runs set deadline_at=now()-interval '1 second' where id in(select second from parameter_test_context);
set local role authenticated;
do $$ declare actor record; result jsonb; worker text:=repeat('synthetic',8); begin
 for actor in select * from pg_temp.parameter_test_context order by label loop
  perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
  result:=public.parameter_history(actor.report,worker);
  perform pg_temp.check_parameter(exists(select 1 from jsonb_array_elements(result) r where r->>'id'=actor.second::text and r->>'error_category'='interrupted'),'expired attempt recovered');
  perform pg_temp.check_parameter(not public.parameter_finish(actor.report,actor.second,'[]','[]',null,worker),'late completion fenced');
  result:=public.parameter_request(actor.report,actor.source,gen_random_uuid(),'v3','aliases-v3',worker);
  perform pg_temp.check_parameter(result->'run'->>'attempt'='3','retry after interruption');
  if actor.label='A' then
   perform public.report_begin_delete(actor.report);
   perform pg_temp.check_parameter((select count(*) from public.report_parameter_reviews)=0,'deletion removes derived access');
   perform pg_temp.deny_parameter(format('select public.parameter_finish(%L,%L,''[]'',''[]'',null,%L)',actor.report,result->'run'->>'id',worker),'P0001');
  end if;
 end loop;
end; $$;
reset role;
do $$ begin
 perform pg_temp.check_parameter(not exists(select 1 from public.report_parameter_runs where report_id=(select report from parameter_test_context where label='A')),'deletion physically cascades attempts');
 perform pg_temp.check_parameter(not exists(select 1 from public.report_parameter_candidates where id=(select candidate from parameter_test_context where label='A')),'deletion physically cascades candidates');
 perform pg_temp.check_parameter(not exists(select 1 from public.report_parameter_reviews where candidate_id=(select candidate from parameter_test_context where label='A')),'deletion physically cascades reviews');
end; $$;
delete from auth.sessions where id=(select session from parameter_test_context where label='B');
set local role authenticated;
do $$ declare actor record; begin
 select * into actor from pg_temp.parameter_test_context where label='B';
 perform set_config('request.jwt.claims',jsonb_build_object('sub',actor.owner,'session_id',actor.session,'role','authenticated','is_anonymous',false)::text,true);
 perform pg_temp.check_parameter((select count(*) from public.report_parameter_candidates)=0,'revoked candidate RLS');
 perform pg_temp.check_parameter((select count(*) from public.report_parameter_reviews)=0,'revoked review RLS');
 perform pg_temp.deny_parameter(format('select public.parameter_history(%L,%L)',actor.report,repeat('synthetic',8)),'28000');
end; $$;
reset role;
rollback;
