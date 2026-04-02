-- MedPort Foundation Schema
-- Run this in Supabase Dashboard → SQL Editor
-- SAFE to run multiple times — all statements use IF NOT EXISTS
-- Creates every table the app needs that wasn't in the original supabase_schema.sql

-- ─────────────────────────────────────────────────────────────────────────────
-- HELPER: anon full-access policy (reused pattern across all tables)
-- ─────────────────────────────────────────────────────────────────────────────

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. team_members
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_members (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  role          TEXT DEFAULT 'Team Member',
  email         TEXT,
  department    TEXT DEFAULT 'unassigned'
                  CHECK (department IN ('marketing','finance','tech','operations','leadership','unassigned')),
  department_color TEXT DEFAULT '#00B89F',
  avatar_color  TEXT DEFAULT '#00B89F',
  is_active     BOOLEAN DEFAULT true,
  sort_order    INT DEFAULT 0,
  joined_at     TIMESTAMPTZ DEFAULT now(),
  last_seen_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='team_members' AND policyname='anon all team_members'
  ) THEN
    CREATE POLICY "anon all team_members" ON team_members FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. team_cards  (disciplinary cards)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_cards (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_email         TEXT NOT NULL,
  member_name          TEXT NOT NULL,
  card_type            TEXT NOT NULL CHECK (card_type IN ('grey','yellow','red')),
  reason               TEXT NOT NULL,
  issued_by_email      TEXT NOT NULL,
  issued_by_name       TEXT NOT NULL,
  is_active            BOOLEAN DEFAULT true,
  auto_escalated_from  UUID REFERENCES team_cards(id),
  created_at           TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE team_cards ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='team_cards' AND policyname='anon all team_cards'
  ) THEN
    CREATE POLICY "anon all team_cards" ON team_cards FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. tasks
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title          TEXT NOT NULL,
  description    TEXT,
  status         TEXT DEFAULT 'open' CHECK (status IN ('open','in_progress','completed','blocked')),
  priority       TEXT DEFAULT 'medium' CHECK (priority IN ('low','medium','high','urgent')),
  assigned_to    TEXT[],
  created_by     TEXT,
  due_date       DATE,
  tags           TEXT[] DEFAULT '{}',
  department     TEXT,
  sprint_id      UUID,
  is_recurring   BOOLEAN DEFAULT false,
  recurrence_type TEXT,
  is_public      BOOLEAN DEFAULT false,
  public_note    TEXT,
  parent_task_id UUID,
  google_event_id TEXT,
  created_at     TIMESTAMPTZ DEFAULT now(),
  updated_at     TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='tasks' AND policyname='anon all tasks'
  ) THEN
    CREATE POLICY "anon all tasks" ON tasks FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. team_goals
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS team_goals (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  description TEXT,
  target      NUMERIC,
  current     NUMERIC DEFAULT 0,
  unit        TEXT DEFAULT '',
  due_date    DATE,
  owner       TEXT,
  status      TEXT DEFAULT 'active' CHECK (status IN ('active','completed','cancelled')),
  created_by  TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE team_goals ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='team_goals' AND policyname='anon all team_goals'
  ) THEN
    CREATE POLICY "anon all team_goals" ON team_goals FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. activity_log
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_email  TEXT NOT NULL,
  actor_name   TEXT NOT NULL,
  action_type  TEXT NOT NULL,
  entity_type  TEXT,
  entity_id    TEXT,
  entity_name  TEXT,
  details      JSONB DEFAULT '{}',
  created_at   TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='activity_log' AND policyname='anon all activity_log'
  ) THEN
    CREATE POLICY "anon all activity_log" ON activity_log FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. saved_searches
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS saved_searches (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner      TEXT NOT NULL,
  name       TEXT NOT NULL,
  filters    JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='saved_searches' AND policyname='anon all saved_searches'
  ) THEN
    CREATE POLICY "anon all saved_searches" ON saved_searches FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. announcements + announcement_reads
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS announcements (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title             TEXT NOT NULL,
  body              TEXT NOT NULL,
  priority          TEXT DEFAULT 'info' CHECK (priority IN ('info','warning','urgent')),
  created_by_email  TEXT NOT NULL,
  created_by_name   TEXT NOT NULL,
  is_active         BOOLEAN DEFAULT true,
  expires_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='announcements' AND policyname='anon all announcements'
  ) THEN
    CREATE POLICY "anon all announcements" ON announcements FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS announcement_reads (
  announcement_id UUID REFERENCES announcements(id) ON DELETE CASCADE,
  email           TEXT NOT NULL,
  read_at         TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (announcement_id, email)
);

ALTER TABLE announcement_reads ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='announcement_reads' AND policyname='anon all announcement_reads'
  ) THEN
    CREATE POLICY "anon all announcement_reads" ON announcement_reads FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. standup_logs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS standup_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_email  TEXT NOT NULL,
  author_name   TEXT NOT NULL,
  yesterday     TEXT,
  today         TEXT NOT NULL,
  blockers      TEXT,
  submitted_at  TIMESTAMPTZ DEFAULT now(),
  date          DATE DEFAULT CURRENT_DATE
);

ALTER TABLE standup_logs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='standup_logs' AND policyname='anon all standup_logs'
  ) THEN
    CREATE POLICY "anon all standup_logs" ON standup_logs FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. wiki_pages
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wiki_pages (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title             TEXT NOT NULL,
  content           TEXT NOT NULL,
  category          TEXT DEFAULT 'general',
  created_by_email  TEXT NOT NULL,
  updated_by_email  TEXT,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE wiki_pages ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='wiki_pages' AND policyname='anon all wiki_pages'
  ) THEN
    CREATE POLICY "anon all wiki_pages" ON wiki_pages FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. notifications
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_email  TEXT NOT NULL,
  type             TEXT NOT NULL,
  title            TEXT NOT NULL,
  body             TEXT,
  link_page        TEXT,
  link_id          TEXT,
  is_read          BOOLEAN DEFAULT false,
  created_at       TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='notifications' AND policyname='anon all notifications'
  ) THEN
    CREATE POLICY "anon all notifications" ON notifications FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 11. task_comments
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS task_comments (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id      UUID REFERENCES tasks(id) ON DELETE CASCADE,
  author_email TEXT NOT NULL,
  author_name  TEXT NOT NULL,
  content      TEXT NOT NULL,
  mentions     TEXT[] DEFAULT '{}',
  created_at   TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE task_comments ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='task_comments' AND policyname='anon all task_comments'
  ) THEN
    CREATE POLICY "anon all task_comments" ON task_comments FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 12. one_on_ones
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS one_on_ones (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_email   TEXT NOT NULL,
  member_name    TEXT NOT NULL,
  scheduled_date DATE NOT NULL,
  agenda         JSONB DEFAULT '[]',
  notes          TEXT,
  action_items   JSONB DEFAULT '[]',
  status         TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled','completed','cancelled')),
  created_at     TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE one_on_ones ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='one_on_ones' AND policyname='anon all one_on_ones'
  ) THEN
    CREATE POLICY "anon all one_on_ones" ON one_on_ones FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 13. messages  (team chat)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel      TEXT NOT NULL,
  sender_email TEXT NOT NULL,
  sender_name  TEXT NOT NULL,
  content      TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_channel_idx ON messages (channel, created_at DESC);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='messages' AND policyname='anon all messages'
  ) THEN
    CREATE POLICY "anon all messages" ON messages FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 14. sprints
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sprints (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         TEXT NOT NULL,
  description  TEXT,
  start_date   DATE,
  end_date     DATE,
  status       TEXT DEFAULT 'active' CHECK (status IN ('active','completed','cancelled')),
  created_by_email TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE sprints ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='sprints' AND policyname='anon all sprints'
  ) THEN
    CREATE POLICY "anon all sprints" ON sprints FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- Add sprint_id to tasks if not present
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='sprint_id'
  ) THEN
    ALTER TABLE tasks ADD COLUMN sprint_id UUID REFERENCES sprints(id);
  END IF;
END $$;
