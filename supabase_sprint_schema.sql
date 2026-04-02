-- MedPort Sprint Schema
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS sprints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL CHECK (length(name) <= 100),
  description TEXT CHECK (length(description) <= 1000),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT DEFAULT 'active' CHECK (status IN ('planned','active','completed')),
  created_by_email TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sprints_status ON sprints (status);

ALTER TABLE sprints ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'sprints' AND policyname = 'anon_all_sprints'
  ) THEN
    CREATE POLICY anon_all_sprints ON sprints
      FOR ALL TO anon USING (true) WITH CHECK (true);
  END IF;
END $$;

-- Add sprint_id to tasks if not present
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'tasks' AND column_name = 'sprint_id'
  ) THEN
    ALTER TABLE tasks ADD COLUMN sprint_id UUID REFERENCES sprints(id);
  END IF;
END $$;
