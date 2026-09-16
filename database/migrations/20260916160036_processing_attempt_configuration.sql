-- Preserve planned processor/configuration even when extraction fails or is interrupted.
begin;
create function swasthyalens_private.processing_request_configured(
  p_report_id uuid, p_idempotency_key uuid, p_worker_secret text,
  p_processor text, p_configuration jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb; run public.report_processing_runs%rowtype;
begin
  perform swasthyalens_private.processing_require_worker(p_worker_secret);
  if p_processor is null or length(p_processor) not between 1 and 500
    or jsonb_typeof(p_configuration) is distinct from 'object'
    or octet_length(p_configuration::text)>4000 then
    raise exception using errcode='P0001', message='report_conflict'; end if;
  result := swasthyalens_private.processing_request(p_report_id,p_idempotency_key,p_worker_secret);
  update public.report_processing_runs set processor=p_processor, configuration=p_configuration
    where id=(result->>'id')::uuid and status='queued' and processor is null;
  select * into run from public.report_processing_runs where id=(result->>'id')::uuid;
  return to_jsonb(run);
end; $$;
create function public.processing_request_configured(
  p_report_id uuid, p_idempotency_key uuid, p_worker_secret text,
  p_processor text, p_configuration jsonb)
returns jsonb language sql security invoker set search_path='' as $$
  select swasthyalens_private.processing_request_configured(
    p_report_id,p_idempotency_key,p_worker_secret,p_processor,p_configuration); $$;
revoke all on function
  swasthyalens_private.processing_request_configured(uuid,uuid,text,text,jsonb),
  public.processing_request_configured(uuid,uuid,text,text,jsonb)
  from public,anon,authenticated,service_role;
grant execute on function
  swasthyalens_private.processing_request_configured(uuid,uuid,text,text,jsonb),
  public.processing_request_configured(uuid,uuid,text,text,jsonb) to authenticated;
commit;
