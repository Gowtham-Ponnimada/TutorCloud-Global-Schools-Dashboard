CREATE OR REPLACE VIEW us.vw_dashboard_readiness AS
SELECT 'dim_states' AS table_name, COUNT(*)::bigint AS row_count FROM us.dim_states
UNION ALL
SELECT 'dim_districts', COUNT(*)::bigint FROM us.dim_districts
UNION ALL
SELECT 'dim_schools', COUNT(*)::bigint FROM us.dim_schools
UNION ALL
SELECT 'fact_enrollment', COUNT(*)::bigint FROM us.fact_enrollment
UNION ALL
SELECT 'fact_staff', COUNT(*)::bigint FROM us.fact_staff
UNION ALL
SELECT 'fact_school_characteristics', COUNT(*)::bigint FROM us.fact_school_characteristics
UNION ALL
SELECT 'fact_performance_state', COUNT(*)::bigint FROM us.fact_performance_state;

CREATE OR REPLACE VIEW us.vw_school_counts_by_state AS
SELECT
    school_year,
    state_name,
    state_abbr,
    COUNT(DISTINCT school_id) AS school_count,
    COUNT(DISTINCT district_id) AS district_count
FROM us.dim_schools
GROUP BY 1,2,3
ORDER BY school_count DESC, state_name;
