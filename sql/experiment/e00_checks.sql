-- Question: Is the experiment table internally consistent?
-- Output: one row per check; n_rows counts the offending rows (all should be 0).
-- Concepts: conditional counting with FILTER, COUNT(column) skips NULLs (so
--           COUNT(*) - COUNT(col) counts them), logical implications as filters.
SELECT 'rows (expect 64000)' AS check_name, COUNT(*) AS n_rows FROM hillstrom
UNION ALL
SELECT 'cells with NULL',
       12 * COUNT(*) - (COUNT(recency) + COUNT(history_segment) + COUNT(history)
                        + COUNT(mens) + COUNT(womens) + COUNT(zip_code) + COUNT(newbie)
                        + COUNT(channel) + COUNT(segment) + COUNT(visit)
                        + COUNT(conversion) + COUNT(spend))
FROM hillstrom
UNION ALL
SELECT 'unexpected segment label',
       COUNT(*) FILTER (WHERE segment NOT IN ('No E-Mail', 'Mens E-Mail', 'Womens E-Mail')) FROM hillstrom
UNION ALL
SELECT 'conversion without a visit',
       COUNT(*) FILTER (WHERE conversion = 1 AND visit = 0) FROM hillstrom
UNION ALL
SELECT 'spend > 0 without conversion',
       COUNT(*) FILTER (WHERE spend > 0 AND conversion = 0) FROM hillstrom
UNION ALL
SELECT 'conversion with zero spend',
       COUNT(*) FILTER (WHERE conversion = 1 AND spend = 0) FROM hillstrom
UNION ALL
SELECT 'negative spend or history',
       COUNT(*) FILTER (WHERE spend < 0 OR history < 0) FROM hillstrom
UNION ALL
SELECT 'bought neither mens nor womens last year',
       COUNT(*) FILTER (WHERE mens = 0 AND womens = 0) FROM hillstrom
UNION ALL
SELECT 'recency outside 1-12 months',
       COUNT(*) FILTER (WHERE recency NOT BETWEEN 1 AND 12) FROM hillstrom;
