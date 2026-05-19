-- KYC funnel conversion with cumulative signup percentage and prior-step drop rate.
-- Bind :start_date and :end_date as ISO timestamps, or pass NULL to disable either filter.
WITH filtered_events AS (
    SELECT
        user_id,
        step_name,
        step_order,
        timestamp
    FROM funnel_events
    WHERE completed = 1
      AND (:start_date IS NULL OR timestamp >= :start_date)
      AND (:end_date IS NULL OR timestamp < :end_date)
),
step_counts AS (
    SELECT
        step_order,
        step_name,
        COUNT(DISTINCT user_id) AS users_reached
    FROM filtered_events
    GROUP BY step_order, step_name
),
windowed AS (
    SELECT
        step_order,
        step_name,
        users_reached,
        LAG(users_reached) OVER (ORDER BY step_order ASC) AS previous_users,
        FIRST_VALUE(users_reached) OVER (ORDER BY step_order ASC) AS signup_users
    FROM step_counts
)
SELECT
    step_order,
    step_name,
    users_reached,
    ROUND(users_reached * 100.0 / NULLIF(signup_users, 0), 2) AS pct_of_signups,
    CASE
        WHEN previous_users IS NULL THEN 0.0
        ELSE ROUND((1.0 - users_reached * 1.0 / NULLIF(previous_users, 0)) * 100.0, 2)
    END AS drop_rate
FROM windowed
ORDER BY step_order ASC;
