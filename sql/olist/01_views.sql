-- Cleaned, analysis-ready views on top of the raw Olist tables.
-- Every query in this folder reads these views, so each cleaning rule lives in one place.

-- Months with complete, non-trivial order volume. Olist has only a few hundred orders
-- before 2017 (with whole months missing) and almost none after August 2018, so trend
-- and cohort queries use this window. See 00_checks.sql / results/olist_monthly_raw.csv.
CREATE OR REPLACE VIEW analysis_window AS
SELECT DATE '2017-01-01' AS start_date,
       DATE '2018-09-01' AS end_date;        -- exclusive

-- One row per order: fulfilment timestamps, value from its items, and the person key.
CREATE OR REPLACE VIEW order_facts AS
WITH item_totals AS (
    SELECT order_id,
           COUNT(*)           AS n_items,
           SUM(price)         AS item_value,
           SUM(freight_value) AS freight_value
    FROM order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    c.customer_unique_id,                 -- customer_id is per order; this is the person
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp      AS purchased_at,
    o.order_approved_at             AS approved_at,
    o.order_delivered_carrier_date  AS shipped_at,
    o.order_delivered_customer_date AS delivered_at,
    o.order_estimated_delivery_date AS estimated_at,
    COALESCE(t.n_items, 0)          AS n_items,
    t.item_value,
    t.freight_value,
    t.item_value + t.freight_value  AS gmv,
    -- A "sale" for revenue and retention: has items and was not canceled / unavailable.
    (o.order_status NOT IN ('canceled', 'unavailable') AND t.order_id IS NOT NULL) AS is_sale
FROM orders o
JOIN customers c USING (customer_id)
LEFT JOIN item_totals t USING (order_id);

-- One review per order. Some orders have several reviews; keep the latest answered one.
CREATE OR REPLACE VIEW order_reviews AS
SELECT order_id, review_score, review_creation_date, review_answer_timestamp
FROM reviews
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id
                           ORDER BY review_answer_timestamp DESC, review_id) = 1;

-- Products with English category names (Portuguese name, then 'unknown', as fallbacks).
CREATE OR REPLACE VIEW products_en AS
SELECT p.product_id,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category
FROM products p
LEFT JOIN category_translation t USING (product_category_name);
