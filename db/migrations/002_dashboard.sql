-- Everything the dashboard shows for one template since a point in time, in one call.
-- Called by the engine (GET /dashboard) via POST /rest/v1/rpc/dashboard. Generic over templates: per-field
-- numbers come from the keys and JSON types inside records.data, so new templates need no new SQL.
create function dashboard(p_template_id text, p_since timestamptz) returns jsonb
language sql
stable
set search_path = public
as $$
  with u as (
    select * from uploads where template_id = p_template_id and created_at >= p_since
  ),
  r as (
    select records.* from records join u on u.id = records.upload_id
  ),
  -- One row per (record, field) with the value's JSON type: 'string', 'number', 'boolean' or 'null'.
  f as (
    select r.id, kv.key as field, kv.value, jsonb_typeof(kv.value) as type
    from r, jsonb_each(r.data) as kv
  ),
  flagged as (
    select fl ->> 'field' as field, count(*) as n
    from r, jsonb_array_elements(r.flags) as fl
    group by 1
  ),
  top as (
    select field, value #>> '{}' as value, count(*) as n,
           row_number() over (partition by field order by count(*) desc, value #>> '{}') as rank
    from f where type = 'string'
    group by field, value
  )
  select jsonb_build_object(
    'totals', (
      select jsonb_build_object(
        'uploads', count(*),
        'records', coalesce(sum(record_count), 0),
        'flags', coalesce(sum(flag_count), 0),
        'confirmed', count(*) filter (where status = 'confirmed'),
        'avg_latency_ms', coalesce(round(avg(latency_ms)), 0)
      )
      from u
    ),
    'per_day', (
      select coalesce(jsonb_agg(jsonb_build_object('day', day, 'uploads', uploads, 'records', records) order by day), '[]')
      from (
        select (created_at at time zone 'UTC')::date as day, count(*) as uploads, sum(record_count) as records
        from u group by 1
      ) d
    ),
    'fields', (
      select coalesce(jsonb_agg(jsonb_build_object(
        'field', s.field,
        'records', s.records,
        'empty', s.empty,
        'flagged', coalesce(flagged.n, 0),
        'true', s.true_count,
        'false', s.false_count,
        'distinct', s.distinct_values,
        'top', coalesce((
          select jsonb_agg(jsonb_build_object('value', top.value, 'count', top.n) order by top.rank)
          from top where top.field = s.field and top.rank <= 6
        ), '[]')
      ) order by s.field), '[]')
      from (
        select field,
               count(*) as records,
               count(*) filter (where type = 'null') as empty,
               count(*) filter (where type = 'boolean' and value = 'true'::jsonb) as true_count,
               count(*) filter (where type = 'boolean' and value = 'false'::jsonb) as false_count,
               count(distinct value) filter (where type = 'string') as distinct_values
        from f group by field
      ) s
      left join flagged on flagged.field = s.field
    ),
    'recent', (
      select coalesce(jsonb_agg(jsonb_build_object(
        'id', id, 'created_at', created_at, 'source', source, 'instructions', instructions,
        'record_count', record_count, 'flag_count', flag_count, 'latency_ms', latency_ms,
        'model', model, 'status', status
      ) order by created_at desc), '[]')
      from (select * from u order by created_at desc limit 10) latest
    )
  );
$$;

-- Only the service role (the engine) may call it.
revoke execute on function dashboard(text, timestamptz) from public, anon, authenticated;
