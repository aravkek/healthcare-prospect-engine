-- Fix status check constraint to match app's STATUS_ORDER values
ALTER TABLE prospects DROP CONSTRAINT IF EXISTS prospects_status_check;

ALTER TABLE prospects
  ADD CONSTRAINT prospects_status_check
  CHECK (status IN (
    'not_contacted',
    'email_sent',
    'pending_response',
    'demo_booked',
    'converted',
    'declined'
  ));

-- Fix any rows that have old status values
UPDATE prospects SET status = 'email_sent'       WHERE status = 'contacted';
UPDATE prospects SET status = 'pending_response' WHERE status = 'responded';
UPDATE prospects SET status = 'demo_booked'      WHERE status = 'meeting_booked';
