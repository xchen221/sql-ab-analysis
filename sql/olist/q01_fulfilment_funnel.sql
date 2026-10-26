-- Question: Of the orders placed, what share reaches each fulfilment stage
--           (payment approved -> handed to carrier -> delivered), and where are
--           orders lost?
-- Definition: an order has reached a stage if that stage's timestamp exists OR it
--           reached a later stage (a delivered order with a missing approval
--           timestamp was still approved; the gap is a logging problem). This keeps
--           the funnel monotone. The last month of the window is excluded so that
--           orders still in transit are not counted as lost.
-- Concepts: chained CTEs, boolean flags, COUNT(*) FILTER (WHERE ...), UNION ALL to turn
--           columns into rows, window functions FIRST_VALUE and LAG.
WITH base AS (
    SELECT f.*
    FROM order_facts f, analysis_window w
    WHERE f.purchased_at >= w.start_date
      AND f.purchased_at <  w.end_date - INTERVAL 1 MONTH
),
delivered AS (
    SELECT *, (order_status = 'delivered' AND delivered_at IS NOT NULL) AS f_delivered
    FROM base
),
shipped AS (
    SELECT *, (f_delivered OR shipped_at IS NOT NULL) AS f_shipped
    FROM delivered
),
flags AS (
    SELECT *, (f_shipped OR approved_at IS NOT NULL) AS f_approved
    FROM shipped
),
stages AS (
    SELECT 1 AS step, 'placed' AS stage, COUNT(*) AS n_orders FROM flags
    UNION ALL SELECT 2, 'approved',  COUNT(*) FILTER (WHERE f_approved)  FROM flags
    UNION ALL SELECT 3, 'shipped',   COUNT(*) FILTER (WHERE f_shipped)   FROM flags
    UNION ALL SELECT 4, 'delivered', COUNT(*) FILTER (WHERE f_delivered) FROM flags
)
SELECT
    step,
    stage,
    n_orders,
    ROUND(100.0 * n_orders / FIRST_VALUE(n_orders) OVER (ORDER BY step), 2) AS pct_of_placed,
    ROUND(100.0 * n_orders / LAG(n_orders) OVER (ORDER BY step), 2)         AS pct_of_previous_step,
    LAG(n_orders) OVER (ORDER BY step) - n_orders                           AS lost_at_this_step
FROM stages
ORDER BY step;
