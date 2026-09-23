-- Uploads and the records extracted from them. Written by the engine (engine/app), which connects with
-- the service role; the site and browsers never query these tables directly.
--
-- Change the data model by adding a new numbered file (002_...sql), not by editing this one.
-- The fields inside records.data are defined per template in templates/*.json ("schema").

-- One row per photo sent to POST /extract.
create table uploads (
  id                  uuid primary key default gen_random_uuid(),
  created_at          timestamptz not null default now(),

  template_id         text not null,              -- e.g. 'attendance'
  source              text not null default 'web', -- 'web' (the site) or 'api' (direct callers)
  instructions        text,                        -- the user's note, as cleaned by the engine

  model               text not null,               -- e.g. 'openbmb/MiniCPM-V-4_5'
  structured_output   boolean not null,            -- false if the model fell back to plain JSON mode
  latency_ms          integer not null,
  prompt_tokens       integer not null default 0,
  completion_tokens   integer not null default 0,

  image_width         integer not null,            -- after resizing; the photo itself is never stored
  image_height        integer not null,
  image_format        text not null,               -- format as uploaded: JPEG, PNG, WEBP, HEIF

  record_count        integer not null,
  flag_count          integer not null,

  status              text not null default 'extracted'
                      check (status in ('extracted', 'confirmed')),
  confirmed_at        timestamptz
);

-- One row per record the engine read (e.g. one person on an attendance sheet).
create table records (
  id                  uuid primary key default gen_random_uuid(),
  upload_id           uuid not null references uploads (id) on delete cascade,
  position            integer not null,            -- order on the page, starting at 0
  template_id         text not null,               -- copied from the upload, for simpler dashboard queries

  data                jsonb not null,              -- the record as extracted, e.g. {"name": ..., "signed": true}
  flags               jsonb not null default '[]', -- [{"field": "phone", "reason": "unreadable"}, ...]
  confirmed_data      jsonb,                       -- the record after a person checked and corrected it

  created_at          timestamptz not null default now(),
  unique (upload_id, position)
);

create index uploads_created_at_idx on uploads (created_at desc);
create index uploads_template_id_idx on uploads (template_id);
create index records_upload_id_idx on records (upload_id);
create index records_template_id_idx on records (template_id);

-- Row level security on, with no policies: only the service role (the engine) can read or write.
-- Add read policies later if the dashboard queries Supabase directly.
alter table uploads enable row level security;
alter table records enable row level security;

-- Saves an upload and its records in one transaction; called by the engine via POST /rest/v1/rpc/save_upload.
-- p_upload: the uploads columns as JSON. p_records: [{"data": {...}, "flags": [...]}, ...] in page order.
create function save_upload(p_upload jsonb, p_records jsonb) returns uuid
language plpgsql
set search_path = public
as $$
declare
  new_id uuid;
begin
  insert into uploads (
    template_id, source, instructions, model, structured_output, latency_ms, prompt_tokens,
    completion_tokens, image_width, image_height, image_format, record_count, flag_count
  )
  select template_id, coalesce(source, 'web'), instructions, model, structured_output, latency_ms,
         coalesce(prompt_tokens, 0), coalesce(completion_tokens, 0), image_width, image_height,
         image_format, record_count, flag_count
  from jsonb_populate_record(null::uploads, p_upload)
  returning id into new_id;

  insert into records (upload_id, position, template_id, data, flags)
  select new_id, r.ordinality - 1, p_upload ->> 'template_id', r.value -> 'data',
         coalesce(r.value -> 'flags', '[]'::jsonb)
  from jsonb_array_elements(p_records) with ordinality as r;

  return new_id;
end;
$$;

-- Only the service role may call it.
revoke execute on function save_upload(jsonb, jsonb) from public, anon, authenticated;
