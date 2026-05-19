-- Hourly market volume profile with peak-hour labeling.
WITH hourly AS (
    SELECT
        strftime('%H', datetime(timestamp, '+5 hours', '+30 minutes')) AS hour_ist,
        AVG(total_volume) AS avg_volume,
        SUM(total_volume) AS total_volume,
        AVG(price_change_24h) AS avg_price_change
    FROM market_data
    GROUP BY strftime('%H', datetime(timestamp, '+5 hours', '+30 minutes'))
),
ranked AS (
    SELECT
        hour_ist,
        avg_volume,
        total_volume,
        avg_price_change,
        RANK() OVER (ORDER BY avg_volume DESC) AS volume_rank
    FROM hourly
)
SELECT
    hour_ist,
    ROUND(avg_volume, 2) AS avg_volume,
    ROUND(total_volume, 2) AS total_volume,
    ROUND(avg_price_change, 2) AS avg_price_change,
    CASE WHEN volume_rank = 1 THEN 'Peak Hour' ELSE 'Normal Hour' END AS peak_hour_label
FROM ranked
ORDER BY hour_ist ASC;
