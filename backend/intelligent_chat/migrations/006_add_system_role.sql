-- ============================================================================
-- ADD 'system' ROLE TO ic_messages
-- Allows context injection messages (e.g., dog deletion notifications)
-- ============================================================================

-- Drop the old constraint
ALTER TABLE ic_messages DROP CONSTRAINT IF EXISTS ic_messages_role_check;

-- Add new constraint with 'system' role
ALTER TABLE ic_messages ADD CONSTRAINT ic_messages_role_check 
    CHECK (role IN ('user', 'assistant', 'system'));

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- After running this migration, you can verify with:
-- SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint 
-- WHERE conrelid = 'ic_messages'::regclass AND conname = 'ic_messages_role_check';


