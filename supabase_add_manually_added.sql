-- Add manually_added flag to prospects table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='prospects' AND column_name='manually_added'
    ) THEN
        ALTER TABLE prospects ADD COLUMN manually_added BOOLEAN DEFAULT false;
    END IF;
END $$;
