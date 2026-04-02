-- MedPort v2 Schema Migration
-- Run in Supabase SQL Editor
-- Idempotent: safe to run multiple times

-- ============================================================
-- 1. ALTER team_members — add columns if they don't exist
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'team_members' AND column_name = 'department'
    ) THEN
        ALTER TABLE team_members
            ADD COLUMN department TEXT DEFAULT 'unassigned'
                CHECK (department IN ('marketing','finance','tech','operations','leadership','unassigned'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'team_members' AND column_name = 'department_color'
    ) THEN
        ALTER TABLE team_members
            ADD COLUMN department_color TEXT DEFAULT '#00B89F';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'team_members' AND column_name = 'joined_at'
    ) THEN
        ALTER TABLE team_members
            ADD COLUMN joined_at TIMESTAMPTZ DEFAULT now();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'team_members' AND column_name = 'last_seen_at'
    ) THEN
        ALTER TABLE team_members
            ADD COLUMN last_seen_at TIMESTAMPTZ;
    END IF;
END $$;

-- ============================================================
-- 2. ALTER tasks — add columns if they don't exist
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'department'
    ) THEN
        ALTER TABLE tasks ADD COLUMN department TEXT DEFAULT NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'tags'
    ) THEN
        ALTER TABLE tasks ADD COLUMN tags TEXT[] DEFAULT '{}';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'is_recurring'
    ) THEN
        ALTER TABLE tasks ADD COLUMN is_recurring BOOLEAN DEFAULT false;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'recurrence_type'
    ) THEN
        ALTER TABLE tasks ADD COLUMN recurrence_type TEXT DEFAULT NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'parent_task_id'
    ) THEN
        ALTER TABLE tasks ADD COLUMN parent_task_id UUID REFERENCES tasks(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE tasks ADD COLUMN is_public BOOLEAN DEFAULT false;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'public_note'
    ) THEN
        ALTER TABLE tasks ADD COLUMN public_note TEXT DEFAULT NULL;
    END IF;
END $$;

-- ============================================================
-- 3. CREATE TABLE task_comments
-- ============================================================

CREATE TABLE IF NOT EXISTS task_comments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id      UUID        REFERENCES tasks(id) ON DELETE CASCADE,
    author_email TEXT        NOT NULL,
    author_name  TEXT        NOT NULL,
    content      TEXT        NOT NULL CHECK (length(content) <= 2000),
    mentions     TEXT[]      DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 4. CREATE TABLE announcements
-- ============================================================

CREATE TABLE IF NOT EXISTS announcements (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT        NOT NULL CHECK (length(title) <= 200),
    body             TEXT        NOT NULL CHECK (length(body) <= 5000),
    priority         TEXT        DEFAULT 'info' CHECK (priority IN ('info','warning','urgent')),
    created_by_email TEXT        NOT NULL,
    created_by_name  TEXT        NOT NULL,
    is_active        BOOLEAN     DEFAULT true,
    expires_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 5. CREATE TABLE announcement_reads
-- ============================================================

CREATE TABLE IF NOT EXISTS announcement_reads (
    announcement_id UUID        REFERENCES announcements(id) ON DELETE CASCADE,
    email           TEXT        NOT NULL,
    read_at         TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (announcement_id, email)
);

-- ============================================================
-- 6. CREATE TABLE standup_logs
-- ============================================================

CREATE TABLE IF NOT EXISTS standup_logs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    author_email TEXT        NOT NULL,
    author_name  TEXT        NOT NULL,
    yesterday    TEXT        CHECK (length(yesterday) <= 2000),
    today        TEXT        NOT NULL CHECK (length(today) <= 2000),
    blockers     TEXT        CHECK (length(blockers) <= 1000),
    submitted_at TIMESTAMPTZ DEFAULT now(),
    date         DATE        DEFAULT CURRENT_DATE
);

-- ============================================================
-- 7. CREATE TABLE wiki_pages
-- ============================================================

CREATE TABLE IF NOT EXISTS wiki_pages (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT        NOT NULL CHECK (length(title) <= 200),
    content          TEXT        NOT NULL CHECK (length(content) <= 50000),
    category         TEXT        DEFAULT 'general'
                                 CHECK (category IN ('general','sop','playbook','onboarding','resources')),
    created_by_email TEXT        NOT NULL,
    updated_by_email TEXT,
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 8. CREATE TABLE notifications
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_email TEXT        NOT NULL,
    type            TEXT        NOT NULL
                                CHECK (type IN ('task_assigned','card_issued','mention','announcement','standup_reminder')),
    title           TEXT        NOT NULL CHECK (length(title) <= 200),
    body            TEXT        CHECK (length(body) <= 500),
    link_page       TEXT,
    link_id         TEXT,
    is_read         BOOLEAN     DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 9. CREATE TABLE one_on_ones
-- ============================================================

CREATE TABLE IF NOT EXISTS one_on_ones (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    member_email   TEXT        NOT NULL,
    member_name    TEXT        NOT NULL,
    scheduled_date DATE        NOT NULL,
    agenda         JSONB       DEFAULT '[]',
    notes          TEXT        CHECK (length(notes) <= 10000),
    action_items   JSONB       DEFAULT '[]',
    status         TEXT        DEFAULT 'scheduled'
                               CHECK (status IN ('scheduled','completed','cancelled')),
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- ROW LEVEL SECURITY — new tables
-- ============================================================

ALTER TABLE task_comments      ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements      ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcement_reads ENABLE ROW LEVEL SECURITY;
ALTER TABLE standup_logs       ENABLE ROW LEVEL SECURITY;
ALTER TABLE wiki_pages         ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications      ENABLE ROW LEVEL SECURITY;
ALTER TABLE one_on_ones        ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'task_comments' AND policyname = 'anon_all_task_comments'
    ) THEN
        CREATE POLICY anon_all_task_comments ON task_comments
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'announcements' AND policyname = 'anon_all_announcements'
    ) THEN
        CREATE POLICY anon_all_announcements ON announcements
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'announcement_reads' AND policyname = 'anon_all_announcement_reads'
    ) THEN
        CREATE POLICY anon_all_announcement_reads ON announcement_reads
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'standup_logs' AND policyname = 'anon_all_standup_logs'
    ) THEN
        CREATE POLICY anon_all_standup_logs ON standup_logs
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'wiki_pages' AND policyname = 'anon_all_wiki_pages'
    ) THEN
        CREATE POLICY anon_all_wiki_pages ON wiki_pages
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'notifications' AND policyname = 'anon_all_notifications'
    ) THEN
        CREATE POLICY anon_all_notifications ON notifications
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'one_on_ones' AND policyname = 'anon_all_one_on_ones'
    ) THEN
        CREATE POLICY anon_all_one_on_ones ON one_on_ones
            FOR ALL TO anon USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ============================================================
-- INDEXES
-- ============================================================

-- notifications: recipient_email + is_read (fetch unread notifications per user)
CREATE INDEX IF NOT EXISTS idx_notifications_recipient_read
    ON notifications (recipient_email, is_read);

-- standup_logs: author_email + date (fetch a member's standup for a given day)
CREATE INDEX IF NOT EXISTS idx_standup_logs_author_date
    ON standup_logs (author_email, date);

-- task_comments: task_id (fetch all comments for a task)
CREATE INDEX IF NOT EXISTS idx_task_comments_task_id
    ON task_comments (task_id);

-- announcements: is_active (fetch active announcements banner)
CREATE INDEX IF NOT EXISTS idx_announcements_is_active
    ON announcements (is_active);
