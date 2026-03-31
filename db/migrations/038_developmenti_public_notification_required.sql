-- Migration 038: Add public_notification_required to Development.i council DA tables
--
-- The Development.i portal detail page exposes "Public Notification Required: Yes/No"
-- as an explicit field. Previously this was not captured.

ALTER TABLE ipswich_dev_applications       ADD COLUMN IF NOT EXISTS public_notification_required TEXT;
ALTER TABLE redland_dev_applications       ADD COLUMN IF NOT EXISTS public_notification_required TEXT;
ALTER TABLE sunshinecoast_dev_applications ADD COLUMN IF NOT EXISTS public_notification_required TEXT;
ALTER TABLE toowoomba_dev_applications     ADD COLUMN IF NOT EXISTS public_notification_required TEXT;
ALTER TABLE westerndowns_dev_applications  ADD COLUMN IF NOT EXISTS public_notification_required TEXT;
