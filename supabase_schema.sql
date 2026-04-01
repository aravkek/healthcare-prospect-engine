-- Run this once in your Supabase SQL editor
-- https://supabase.com/dashboard/project/tzvmdwjhzebgqxorkjms/sql

create table if not exists prospects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  inst_type text,
  city text,
  province_state text,
  country text,
  website text,
  phone text,
  email text,
  decision_maker_name text,
  decision_maker_title text,
  decision_maker_linkedin text,
  innovation_score int default 0,
  accessibility_score int default 0,
  fit_score int default 0,
  composite_score int generated always as (innovation_score + accessibility_score + fit_score) stored,
  competitor_risk text default 'none',
  priority_rank int default 3,
  research_notes text,
  outreach_angle text,
  source text,
  -- CRM fields
  status text default 'not_contacted'
    check (status in ('not_contacted','contacted','responded','meeting_booked','declined','converted')),
  assigned_to text,
  contact_notes text,
  last_contacted_at timestamptz,
  outreach_count int default 0,
  -- Metadata
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Upsert on name (deduplication key)
create unique index if not exists prospects_name_idx on prospects (name);

-- RLS: allow anon reads and service-role writes
alter table prospects enable row level security;

create policy "anon can read" on prospects
  for select using (true);

create policy "service role can do everything" on prospects
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- Allow anon to update CRM fields only (status, assigned_to, notes, last_contacted_at, outreach_count)
create policy "anon can update crm fields" on prospects
  for update using (true)
  with check (true);

-- Updated_at trigger
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

create trigger prospects_updated_at
  before update on prospects
  for each row execute function update_updated_at();
