-- Question: Do the arms look alike on everything measured BEFORE the e-mail?
--           (Randomisation should make them differ only by chance.)
-- Output: long format (arm, covariate, mean, sd) so standardized mean differences
--         can be computed for any pair of arms.
-- Concepts: one-hot encoding with CASE, UNPIVOT, AVG / STDDEV_SAMP by group.
WITH encoded AS (
    SELECT
        segment AS arm,
        recency,
        history,
        mens,
        womens,
        newbie,
        CASE WHEN channel  = 'Web'          THEN 1 ELSE 0 END AS channel_web,
        CASE WHEN channel  = 'Phone'        THEN 1 ELSE 0 END AS channel_phone,
        CASE WHEN channel  = 'Multichannel' THEN 1 ELSE 0 END AS channel_multi,
        CASE WHEN zip_code = 'Urban'        THEN 1 ELSE 0 END AS zip_urban,
        CASE WHEN zip_code = 'Surburban'    THEN 1 ELSE 0 END AS zip_suburban,
        CASE WHEN zip_code = 'Rural'        THEN 1 ELSE 0 END AS zip_rural
    FROM hillstrom
),
long AS (
    UNPIVOT encoded
    ON COLUMNS(* EXCLUDE (arm))
    INTO NAME covariate VALUE value
)
SELECT arm, covariate, COUNT(*) AS n, AVG(value) AS mean, STDDEV_SAMP(value) AS sd
FROM long
GROUP BY arm, covariate
ORDER BY covariate, arm;
