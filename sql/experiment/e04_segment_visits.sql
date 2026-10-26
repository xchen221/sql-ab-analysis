-- Question: Does each e-mail work better for customers who bought that kind of
--           merchandise last year? (Exploratory; the confirmatory test is in Python.)
-- Definition: past_category from the pre-treatment flags mens / womens.
-- Concepts: CASE to derive a segment, conditional aggregation into wide columns,
--           arithmetic across aggregated columns.
WITH seg AS (
    SELECT segment AS arm,
           CASE WHEN mens = 1 AND womens = 1 THEN 'both'
                WHEN mens = 1               THEN 'mens only'
                ELSE                             'womens only' END AS past_category,
           visit
    FROM hillstrom
)
SELECT
    past_category,
    COUNT(*) FILTER (WHERE arm = 'No E-Mail')                           AS n_control,
    ROUND(100.0 * AVG(visit) FILTER (WHERE arm = 'No E-Mail'), 2)       AS visit_pct_control,
    ROUND(100.0 * AVG(visit) FILTER (WHERE arm = 'Mens E-Mail'), 2)     AS visit_pct_mens,
    ROUND(100.0 * AVG(visit) FILTER (WHERE arm = 'Womens E-Mail'), 2)   AS visit_pct_womens,
    ROUND(100.0 * (AVG(visit) FILTER (WHERE arm = 'Mens E-Mail')
                 - AVG(visit) FILTER (WHERE arm = 'No E-Mail')), 2)     AS lift_pp_mens,
    ROUND(100.0 * (AVG(visit) FILTER (WHERE arm = 'Womens E-Mail')
                 - AVG(visit) FILTER (WHERE arm = 'No E-Mail')), 2)     AS lift_pp_womens
FROM seg
GROUP BY past_category
ORDER BY past_category;
