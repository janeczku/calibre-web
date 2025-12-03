-- SQL script to enable Audiobooks sidebar for all users
-- SIDEBAR_AUDIOBOOKS = 1 << 18 = 262144
-- This updates all users to add the audiobooks flag to their sidebar_view

-- Update all users to include the audiobooks sidebar option
-- Uses bitwise OR to add the flag without removing existing flags
UPDATE user
SET sidebar_view = sidebar_view | 262144
WHERE (sidebar_view & 262144) = 0;

-- Show the results
SELECT id, name, sidebar_view,
       CASE
           WHEN (sidebar_view & 262144) != 0 THEN 'Enabled'
           ELSE 'Disabled'
       END as audiobooks_status
FROM user;
