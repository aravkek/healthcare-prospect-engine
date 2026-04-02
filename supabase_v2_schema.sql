-- MedPort v2 Schema — run in Supabase SQL editor
-- ================================================

-- Activity log: every action team members take
CREATE TABLE IF NOT EXISTS activity_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_email text NOT NULL,
  actor_name text NOT NULL,
  action_type text NOT NULL,  -- 'status_change','note_added','task_created','task_completed','card_issued','goal_updated','search_run'
  entity_type text NOT NULL,  -- 'prospect','task','card','goal'
  entity_id text,
  entity_name text,
  details jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_activity_log_created_at ON activity_log (created_at DESC);

-- Tasks: individual and group tasks assigned by Arav
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  description text,
  assigned_by_email text NOT NULL,
  assigned_by_name text NOT NULL,
  assigned_to text[] NOT NULL DEFAULT '{}',  -- array of emails
  task_type text NOT NULL DEFAULT 'individual',  -- 'individual','group','team_goal'
  priority text NOT NULL DEFAULT 'medium',  -- 'low','medium','high','urgent'
  status text NOT NULL DEFAULT 'open',  -- 'open','in_progress','completed','blocked'
  due_date date,
  google_calendar_event_id text,
  prospect_id text,
  prospect_name text,
  completed_at timestamptz,
  completed_by text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Team goals: high-level targets set by Arav
CREATE TABLE IF NOT EXISTS team_goals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  description text,
  target_value int NOT NULL DEFAULT 1,
  current_value int NOT NULL DEFAULT 0,
  metric_type text NOT NULL DEFAULT 'custom',  -- 'demos_booked','emails_sent','converted','custom'
  due_date date,
  status text NOT NULL DEFAULT 'active',  -- 'active','completed','paused'
  created_by_email text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Team cards: disciplinary system
-- Rules: 2 grey = 1 yellow auto-escalation, 3 yellow = 1 red, 2 reds = internal review, 3 reds = removed
CREATE TABLE IF NOT EXISTS team_cards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  member_email text NOT NULL,
  member_name text NOT NULL,
  card_type text NOT NULL,  -- 'grey','yellow','red'
  reason text NOT NULL,
  issued_by_email text NOT NULL,
  issued_by_name text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  auto_escalated_from uuid,  -- if this card was auto-generated from escalation
  created_at timestamptz DEFAULT now()
);

-- Saved searches: personal + team filter presets
CREATE TABLE IF NOT EXISTS saved_searches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_email text NOT NULL,
  name text NOT NULL,
  filters jsonb NOT NULL DEFAULT '{}',
  is_team_shared boolean NOT NULL DEFAULT false,
  use_count int NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

-- RLS: allow anon access (same pattern as prospects table)
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_activity" ON activity_log FOR SELECT USING (true);
CREATE POLICY "anon_insert_activity" ON activity_log FOR INSERT WITH CHECK (true);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_all_tasks" ON tasks FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE team_goals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_all_goals" ON team_goals FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE team_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_all_cards" ON team_cards FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_all_searches" ON saved_searches FOR ALL USING (true) WITH CHECK (true);

-- Also add missing columns to prospects if not present
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS startup_receptiveness int DEFAULT 0;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS score_breakdown text;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS emr_system text;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS patient_volume text;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS existing_ai_tools text;
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS phone_intake_evidence text;

-- ─── Team Members ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  role text NOT NULL DEFAULT 'Team Member',
  email text,
  avatar_color text DEFAULT '#00B89F',
  is_active boolean DEFAULT true,
  sort_order int DEFAULT 0,
  created_at timestamptz DEFAULT now()
);
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_all_members" ON team_members FOR ALL USING (true) WITH CHECK (true);

-- Seed with default team (only inserts if name doesn't already exist)
INSERT INTO team_members (name, role, email, sort_order)
SELECT 'Arav', 'CEO & Co-Founder', 'aravkekane@gmail.com', 0
WHERE NOT EXISTS (SELECT 1 FROM team_members WHERE name = 'Arav');
