-- Run this in Supabase Dashboard → SQL Editor
-- Adds new enriched research columns to the prospects table

ALTER TABLE prospects
  ADD COLUMN IF NOT EXISTS startup_receptiveness integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS emr_system text DEFAULT '',
  ADD COLUMN IF NOT EXISTS patient_volume text DEFAULT '',
  ADD COLUMN IF NOT EXISTS existing_ai_tools text DEFAULT '',
  ADD COLUMN IF NOT EXISTS phone_intake_evidence text DEFAULT '',
  ADD COLUMN IF NOT EXISTS score_breakdown text DEFAULT '';

-- Also update the status options comment (no schema change needed — it's just text)
-- Valid status values: not_contacted | email_sent | pending_response | demo_booked | converted | declined
