-- Question: In the seller-acquisition funnel (marketing-qualified lead -> closed
--           deal -> first sale), how do lead sources compare?
-- Definition: a closed deal is "activated" if the seller has a sale within 90 days
--           of the won date. Activation is computed only for deals won at least 90
--           days before the end of the analysis window (order data effectively stop
--           in August 2018), so every deal has a full 90-day window. Sources with
--           fewer than 100 leads are pooled as 'other'. Differences between sources
--           are descriptive: sources attract different kinds of sellers.
-- Concepts: LEFT JOIN chain that keeps unconverted leads, EXISTS (semi-join) for
--           "has at least one", COUNT(DISTINCT), date arithmetic, grouping small
--           categories with a CASE over a window count.
WITH leads AS (
    SELECT m.mql_id,
           COALESCE(m.origin, 'unknown') AS origin_raw,
           m.first_contact_date,
           d.seller_id,
           d.won_date
    FROM mqls m
    LEFT JOIN closed_deals d USING (mql_id)
),
leads_grouped AS (
    SELECT *,
           CASE WHEN COUNT(*) OVER (PARTITION BY origin_raw) >= 100 THEN origin_raw
                ELSE 'other' END AS origin
    FROM leads
),
deals AS (
    SELECT l.*,
           l.won_date < w.end_date - INTERVAL 90 DAY AS has_full_window,
           EXISTS (
               SELECT 1
               FROM order_items i
               JOIN order_facts f USING (order_id)
               WHERE i.seller_id = l.seller_id
                 AND f.is_sale
                 AND f.purchased_at >= l.won_date
                 AND f.purchased_at <  l.won_date + INTERVAL 90 DAY
           ) AS activated_90d
    FROM leads_grouped l
    CROSS JOIN analysis_window w
)
SELECT
    origin,
    COUNT(*)                                                         AS n_leads,
    COUNT(won_date)                                                  AS n_won,
    ROUND(100.0 * COUNT(won_date) / COUNT(*), 1)                     AS pct_won,
    ROUND(QUANTILE_CONT(DATE_DIFF('day', first_contact_date, won_date::DATE), 0.5), 0) AS median_days_to_close,
    COUNT(*) FILTER (WHERE won_date IS NOT NULL AND has_full_window)  AS n_won_full_window,
    ROUND(100.0 * AVG(CASE WHEN activated_90d THEN 1 ELSE 0 END)
          FILTER (WHERE won_date IS NOT NULL AND has_full_window), 1) AS pct_activated_90d
FROM deals
GROUP BY origin
ORDER BY n_leads DESC;
