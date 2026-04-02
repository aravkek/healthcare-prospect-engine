-- MedPort Chat Schema
-- Run in Supabase SQL Editor after supabase_v2_schema.sql

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel TEXT NOT NULL DEFAULT 'general',
  sender_email TEXT NOT NULL,
  sender_name TEXT NOT NULL,
  content TEXT NOT NULL CHECK (length(content) <= 2000),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages (channel, created_at);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'messages' AND policyname = 'anon_all_messages'
  ) THEN
    CREATE POLICY anon_all_messages ON messages
      FOR ALL TO anon
      USING (true)
      WITH CHECK (true);
  END IF;
END $$;
