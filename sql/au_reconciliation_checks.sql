-- Australia reconciliation checks

-- 1) National totals
SELECT
    'total_students' AS metric_name,
    COALESCE(SUM(fst.total_students), 0) AS acara_derived
FROM au.fact_school_totals fst
WHERE fst.school_year = '2025';

-- 2) Sector totals
SELECT
    ds.management_type,
    COUNT(*) AS school_rows,
    COALESCE(SUM(fst.total_students), 0) AS students
FROM au.dim_schools ds
LEFT JOIN au.fact_school_totals fst
  ON ds.school_year = fst.school_year
 AND ds.school_id = fst.school_id
WHERE ds.school_year = '2025'
GROUP BY ds.management_type
ORDER BY students DESC NULLS LAST, ds.management_type;

-- 3) State totals
SELECT
    ds.state_name,
    COUNT(*) AS school_rows,
    COALESCE(SUM(fst.total_students), 0) AS students
FROM au.dim_schools ds
LEFT JOIN au.fact_school_totals fst
  ON ds.school_year = fst.school_year
 AND ds.school_id = fst.school_id
WHERE ds.school_year = '2025'
GROUP BY ds.state_name
ORDER BY students DESC NULLS LAST, ds.state_name;

-- 4) Dashboard readiness
SELECT *
FROM au.vw_dashboard_readiness;

-- 5) Schools with missing total_students
SELECT
    ds.school_id,
    ds.school_name,
    ds.state_name,
    ds.district_name,
    ds.management_type
FROM au.dim_schools ds
LEFT JOIN au.fact_school_totals fst
  ON ds.school_year = fst.school_year
 AND ds.school_id = fst.school_id
WHERE ds.school_year = '2025'
  AND fst.total_students IS NULL
ORDER BY ds.state_name, ds.school_name;

-- 6) Duplicate school IDs
SELECT
    ds.school_id,
    COUNT(*) AS row_count
FROM au.dim_schools ds
WHERE ds.school_year = '2025'
GROUP BY ds.school_id
HAVING COUNT(*) > 1
ORDER BY row_count DESC, ds.school_id;
