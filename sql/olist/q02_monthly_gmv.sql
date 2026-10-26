-- Question: How did monthly orders and GMV develop, month over month and year over
--           year, and which months are complete enough to analyse?
-- Definition: GMV = item price + freight of sale orders (not canceled / unavailable).
--           All months are listed (to justify the analysis window); growth columns
--           are computed inside the window only.
-- Concepts: DATE_TRUNC + GROUP BY, LAG for month-over-month growth, a self-join on
--           "month - 12 months" for year-over-year growth (LAG(12) would silently
--           compare the wrong months if a month were missing), moving average and
--           running total with ROWS frames.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', purchased_at)::DATE AS month,
        COUNT(*)                                AS n_orders_all,
        COUNT(*) FILTER (WHERE is_sale)         AS n_sales,
        SUM(gmv) FILTER (WHERE is_sale)         AS gmv
    FROM order_facts
    GROUP BY 1
),
in_window AS (
    SELECT m.*
    FROM monthly m, analysis_window w
    WHERE m.month >= w.start_date AND m.month < w.end_date
),
growth AS (
    SELECT
        cur.month,
        100.0 * (cur.gmv / LAG(cur.gmv) OVER (ORDER BY cur.month) - 1)          AS gmv_mom_pct,
        100.0 * (cur.gmv / prev.gmv - 1)                                         AS gmv_yoy_pct,
        CASE WHEN COUNT(*) OVER w3 = 3 THEN AVG(cur.gmv) OVER w3 END             AS gmv_3mo_avg,
        SUM(cur.gmv) OVER (ORDER BY cur.month
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)     AS gmv_cumulative
    FROM in_window cur
    LEFT JOIN in_window prev
           ON prev.month = cur.month - INTERVAL 12 MONTH
    WINDOW w3 AS (ORDER BY cur.month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
)
SELECT
    m.month,
    g.month IS NOT NULL                 AS in_window,
    m.n_orders_all,
    m.n_sales,
    ROUND(m.gmv, 0)                     AS gmv,
    ROUND(m.gmv / m.n_sales, 2)         AS avg_order_value,
    ROUND(g.gmv_mom_pct, 1)             AS gmv_mom_pct,
    ROUND(g.gmv_yoy_pct, 1)             AS gmv_yoy_pct,
    ROUND(g.gmv_3mo_avg, 0)             AS gmv_3mo_avg,
    ROUND(g.gmv_cumulative, 0)          AS gmv_cumulative
FROM monthly m
LEFT JOIN growth g USING (month)
ORDER BY m.month;
