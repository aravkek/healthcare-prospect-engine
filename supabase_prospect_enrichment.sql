-- MedPort Prospect Enrichment Schema
-- Run in Supabase SQL Editor (idempotent)

DO $$
BEGIN
    -- Deep research fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='research_brief') THEN
        ALTER TABLE prospects ADD COLUMN research_brief TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='dm_research') THEN
        ALTER TABLE prospects ADD COLUMN dm_research TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='fit_analysis') THEN
        ALTER TABLE prospects ADD COLUMN fit_analysis TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='research_updated_at') THEN
        ALTER TABLE prospects ADD COLUMN research_updated_at TIMESTAMPTZ;
    END IF;
    -- Decision maker contact enrichment
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='decision_maker_email') THEN
        ALTER TABLE prospects ADD COLUMN decision_maker_email TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='decision_maker_phone') THEN
        ALTER TABLE prospects ADD COLUMN decision_maker_phone TEXT;
    END IF;
    -- Email drafts (JSON array of {id, subject, body, variant, created_at})
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='email_drafts') THEN
        ALTER TABLE prospects ADD COLUMN email_drafts JSONB DEFAULT '[]';
    END IF;
    -- Outreach timeline (JSON array of {date, type, subject, notes, outcome, logged_by})
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='outreach_timeline') THEN
        ALTER TABLE prospects ADD COLUMN outreach_timeline JSONB DEFAULT '[]';
    END IF;
    -- Follow-up tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='next_followup_at') THEN
        ALTER TABLE prospects ADD COLUMN next_followup_at DATE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='response_type') THEN
        ALTER TABLE prospects ADD COLUMN response_type TEXT DEFAULT 'none';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='prospects' AND column_name='last_contacted_at') THEN
        ALTER TABLE prospects ADD COLUMN last_contacted_at TIMESTAMPTZ;
    END IF;
END $$;
