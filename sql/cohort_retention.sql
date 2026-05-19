-- Weekly cohort retention for weeks 0 through 7 using SQLite date functions and self-joins.
WITH signup_events AS (
    SELECT
        user_id,
        MIN(timestamp) AS signup_ts,
        strftime('%Y-W%W', MIN(timestamp)) AS cohort_week
    FROM funnel_events
    WHERE step_name = 'email_signup'
      AND completed = 1
    GROUP BY user_id
),
activity_weeks AS (
    SELECT DISTINCT
        e.user_id,
        CAST((julianday(e.timestamp) - julianday(s.signup_ts)) / 7 AS INTEGER) AS week_number
    FROM funnel_events e
    INNER JOIN signup_events s
        ON e.user_id = s.user_id
    WHERE completed = 1
),
cohort_counts AS (
    SELECT
        s.cohort_week,
        COUNT(DISTINCT s.user_id) AS cohort_users,
        COUNT(DISTINCT w0.user_id) AS week_0_users,
        COUNT(DISTINCT w1.user_id) AS week_1_users,
        COUNT(DISTINCT w2.user_id) AS week_2_users,
        COUNT(DISTINCT w3.user_id) AS week_3_users,
        COUNT(DISTINCT w4.user_id) AS week_4_users,
        COUNT(DISTINCT w5.user_id) AS week_5_users,
        COUNT(DISTINCT w6.user_id) AS week_6_users,
        COUNT(DISTINCT w7.user_id) AS week_7_users
    FROM signup_events s
    LEFT JOIN activity_weeks w0 ON s.user_id = w0.user_id AND w0.week_number = 0
    LEFT JOIN activity_weeks w1 ON s.user_id = w1.user_id AND w1.week_number = 1
    LEFT JOIN activity_weeks w2 ON s.user_id = w2.user_id AND w2.week_number = 2
    LEFT JOIN activity_weeks w3 ON s.user_id = w3.user_id AND w3.week_number = 3
    LEFT JOIN activity_weeks w4 ON s.user_id = w4.user_id AND w4.week_number = 4
    LEFT JOIN activity_weeks w5 ON s.user_id = w5.user_id AND w5.week_number = 5
    LEFT JOIN activity_weeks w6 ON s.user_id = w6.user_id AND w6.week_number = 6
    LEFT JOIN activity_weeks w7 ON s.user_id = w7.user_id AND w7.week_number = 7
    GROUP BY s.cohort_week
)
SELECT
    cohort_week,
    week_0_users,
    ROUND(week_0_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_0_retention_pct,
    week_1_users,
    ROUND(week_1_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_1_retention_pct,
    week_2_users,
    ROUND(week_2_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_2_retention_pct,
    week_3_users,
    ROUND(week_3_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_3_retention_pct,
    week_4_users,
    ROUND(week_4_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_4_retention_pct,
    week_5_users,
    ROUND(week_5_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_5_retention_pct,
    week_6_users,
    ROUND(week_6_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_6_retention_pct,
    week_7_users,
    ROUND(week_7_users * 100.0 / NULLIF(cohort_users, 0), 2) AS week_7_retention_pct
FROM cohort_counts
ORDER BY cohort_week ASC;
