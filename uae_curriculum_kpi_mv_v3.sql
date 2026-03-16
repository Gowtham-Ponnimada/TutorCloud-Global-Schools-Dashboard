-- =============================================================================
-- UAE Curriculum KPI Materialized View  (v3 – production-ready)
-- File : uae_curriculum_kpi_mv_v3.sql
-- Purpose : Proportionally allocate student / teacher counts to each curriculum
--           using school-share within (academic_year, region_en, education_type).
-- Aggregate invariant : SUM(mv.student_count) for a given
--   (year, region, education_type) == SUM from uae_fact_enrollment for the
--   same group  (rounding tolerance ±1 per curriculum row).
-- Data availability flags:
--   has_enrollment_data = TRUE  → education_type exists in uae_fact_enrollment
--                                 (currently: Public, Public Ajyal only)
--   has_teacher_data    = TRUE  → education_type exists in uae_fact_teachers_emirate
-- Usage in dashboard:
--   • When curriculum filter active  → query this MV instead of fact tables
--   • When no curriculum filter      → use existing fact-table queries unchanged
-- =============================================================================

-- 0. Drop old version if it exists (safe re-run)
DROP MATERIALIZED VIEW IF EXISTS uae.mv_uae_curriculum_kpi CASCADE;

-- =============================================================================
-- 1.  CREATE MATERIALIZED VIEW
-- =============================================================================
CREATE MATERIALIZED VIEW uae.mv_uae_curriculum_kpi AS
WITH
-- ── Step 1 : school counts per (year, region, edtype, curriculum) ─────────
school_detail AS (
    SELECT
        academic_year,
        region_en,
        education_type,
        curriculum_en,
        SUM(school_count) AS curriculum_schools
    FROM uae.uae_fact_schools
    GROUP BY academic_year, region_en, education_type, curriculum_en
),

-- ── Step 2 : total schools per (year, region, edtype)  ────────────────────
school_totals AS (
    SELECT
        academic_year,
        region_en,
        education_type,
        SUM(curriculum_schools) AS total_schools_edtype
    FROM school_detail
    GROUP BY academic_year, region_en, education_type
),

-- ── Step 3 : enrollment aggregated by (year, region, edtype) ─────────────
--   NOTE: uae_fact_enrollment only contains Public / Public Ajyal rows.
--         LEFT JOIN means private-school rows will get NULL here.
enrollment_agg AS (
    SELECT
        academic_year,
        region_en,
        education_type,
        SUM(student_count)                                              AS total_students,
        SUM(CASE WHEN LOWER(gender) LIKE '%female%' OR LOWER(gender) LIKE '%بنات%'
                 THEN student_count ELSE 0 END)                        AS female_students,
        SUM(CASE WHEN LOWER(gender) LIKE '%male%'  OR LOWER(gender) LIKE '%بنين%'
                 THEN student_count ELSE 0 END)                        AS male_students,
        SUM(CASE WHEN LOWER(COALESCE(nationality_cat,'')) LIKE '%emirati%'
                 OR LOWER(COALESCE(nationality_cat,'')) LIKE '%مواطن%'
                 THEN student_count ELSE 0 END)                        AS emirati_students,
        SUM(CASE WHEN LOWER(COALESCE(nationality_cat,'')) LIKE '%resident%'
                 OR LOWER(COALESCE(nationality_cat,'')) LIKE '%وافد%'
                 THEN student_count ELSE 0 END)                        AS resident_students
    FROM uae.uae_fact_enrollment
    GROUP BY academic_year, region_en, education_type
),

-- ── Step 4 : teacher/staff aggregated by (year, region, edtype) ──────────
teacher_agg AS (
    SELECT
        academic_year,
        region_en,
        education_type,
        SUM(teacher_count)                                              AS total_teachers,
        SUM(staff_count)                                                AS total_staff,
        SUM(CASE WHEN LOWER(gender) LIKE '%female%' OR LOWER(gender) LIKE '%بنات%'
                 THEN teacher_count ELSE 0 END)                        AS female_teachers,
        SUM(CASE WHEN LOWER(gender) LIKE '%male%'  OR LOWER(gender) LIKE '%بنين%'
                 THEN teacher_count ELSE 0 END)                        AS male_teachers,
        SUM(CASE WHEN LOWER(COALESCE(nationality_cat,'')) LIKE '%emirati%'
                 OR LOWER(COALESCE(nationality_cat,'')) LIKE '%مواطن%'
                 THEN teacher_count ELSE 0 END)                        AS emirati_teachers,
        SUM(CASE WHEN LOWER(COALESCE(nationality_cat,'')) LIKE '%resident%'
                 OR LOWER(COALESCE(nationality_cat,'')) LIKE '%وافد%'
                 THEN teacher_count ELSE 0 END)                        AS resident_teachers
    FROM uae.uae_fact_teachers_emirate
    GROUP BY academic_year, region_en, education_type
)

-- ── Final SELECT ──────────────────────────────────────────────────────────
SELECT
    sd.academic_year,
    sd.region_en,
    sd.education_type,
    sd.curriculum_en,

    -- ── School columns (always available) ──────────────────────────────
    sd.curriculum_schools                                               AS school_count,
    st.total_schools_edtype,
    ROUND(
        sd.curriculum_schools::NUMERIC
        / NULLIF(st.total_schools_edtype, 0) * 100,
    2)                                                                  AS school_share_pct,

    -- ── Proportional student counts (NULL when enrollment data absent) ──
    CASE WHEN ea.total_students IS NOT NULL THEN
        ROUND(ea.total_students  * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS student_count,

    CASE WHEN ea.female_students IS NOT NULL THEN
        ROUND(ea.female_students * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS female_students,

    CASE WHEN ea.male_students IS NOT NULL THEN
        ROUND(ea.male_students   * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS male_students,

    CASE WHEN ea.emirati_students IS NOT NULL THEN
        ROUND(ea.emirati_students * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS emirati_students,

    CASE WHEN ea.resident_students IS NOT NULL THEN
        ROUND(ea.resident_students * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS resident_students,

    -- ── Proportional teacher counts (NULL when teacher data absent) ─────
    CASE WHEN ta.total_teachers IS NOT NULL THEN
        ROUND(ta.total_teachers  * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS teacher_count,

    CASE WHEN ta.total_staff IS NOT NULL THEN
        ROUND(ta.total_staff     * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS staff_count,

    CASE WHEN ta.female_teachers IS NOT NULL THEN
        ROUND(ta.female_teachers * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS female_teachers,

    CASE WHEN ta.male_teachers IS NOT NULL THEN
        ROUND(ta.male_teachers   * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS male_teachers,

    CASE WHEN ta.emirati_teachers IS NOT NULL THEN
        ROUND(ta.emirati_teachers * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS emirati_teachers,

    CASE WHEN ta.resident_teachers IS NOT NULL THEN
        ROUND(ta.resident_teachers * sd.curriculum_schools::NUMERIC
              / NULLIF(st.total_schools_edtype, 0))
    ELSE NULL END                                                       AS resident_teachers,

    -- ── Derived ratios ──────────────────────────────────────────────────
    CASE WHEN ea.total_students IS NOT NULL AND ta.total_teachers IS NOT NULL THEN
        ROUND(
            ROUND(ea.total_students  * sd.curriculum_schools::NUMERIC
                  / NULLIF(st.total_schools_edtype, 0))
            / NULLIF(
                ROUND(ta.total_teachers * sd.curriculum_schools::NUMERIC
                      / NULLIF(st.total_schools_edtype, 0)),
              0),
        1)
    ELSE NULL END                                                       AS student_teacher_ratio,

    CASE WHEN ea.total_students IS NOT NULL AND sd.curriculum_schools > 0 THEN
        ROUND(
            ROUND(ea.total_students * sd.curriculum_schools::NUMERIC
                  / NULLIF(st.total_schools_edtype, 0))
            / NULLIF(sd.curriculum_schools, 0),
        1)
    ELSE NULL END                                                       AS students_per_school,

    -- ── Data-availability flags ─────────────────────────────────────────
    -- TRUE  → proportional estimate available (public-school rows)
    -- FALSE → source table has no rows for this education_type (private schools)
    (ea.total_students  IS NOT NULL)                                    AS has_enrollment_data,
    (ta.total_teachers  IS NOT NULL)                                    AS has_teacher_data

FROM school_detail   sd
JOIN  school_totals  st  USING (academic_year, region_en, education_type)
LEFT JOIN enrollment_agg ea USING (academic_year, region_en, education_type)
LEFT JOIN teacher_agg    ta USING (academic_year, region_en, education_type)
;

-- =============================================================================
-- 2.  INDEXES  (for fast dashboard filtering)
-- =============================================================================
CREATE INDEX idx_mv_curr_kpi_year
    ON uae.mv_uae_curriculum_kpi (academic_year);

CREATE INDEX idx_mv_curr_kpi_region
    ON uae.mv_uae_curriculum_kpi (region_en);

CREATE INDEX idx_mv_curr_kpi_curriculum
    ON uae.mv_uae_curriculum_kpi (curriculum_en);

CREATE INDEX idx_mv_curr_kpi_edtype
    ON uae.mv_uae_curriculum_kpi (education_type);

CREATE INDEX idx_mv_curr_kpi_year_region_curr
    ON uae.mv_uae_curriculum_kpi (academic_year, region_en, curriculum_en);

CREATE INDEX idx_mv_curr_kpi_year_curr
    ON uae.mv_uae_curriculum_kpi (academic_year, curriculum_en);

-- =============================================================================
-- 3.  VALIDATION QUERIES  (run after CREATE to confirm aggregate consistency)
-- =============================================================================

-- Check A : student totals in MV must match uae_fact_enrollment totals
--           (rounding diff should be ≤ number of distinct curricula per group)
/*
SELECT
    mv.academic_year,
    mv.region_en,
    mv.education_type,
    SUM(mv.student_count)           AS mv_total_students,
    MAX(ea.total_students)          AS fact_total_students,
    ABS(SUM(mv.student_count) - MAX(ea.total_students)) AS rounding_diff,
    COUNT(*)                        AS num_curricula
FROM uae.mv_uae_curriculum_kpi mv
JOIN (
    SELECT academic_year, region_en, education_type,
           SUM(student_count) AS total_students
    FROM uae.uae_fact_enrollment
    GROUP BY 1, 2, 3
) ea USING (academic_year, region_en, education_type)
WHERE mv.has_enrollment_data = TRUE
GROUP BY mv.academic_year, mv.region_en, mv.education_type
HAVING ABS(SUM(mv.student_count) - MAX(ea.total_students)) > 5
ORDER BY rounding_diff DESC;
*/

-- Check B : teacher totals in MV must match uae_fact_teachers_emirate totals
/*
SELECT
    mv.academic_year,
    mv.region_en,
    mv.education_type,
    SUM(mv.teacher_count)           AS mv_total_teachers,
    MAX(ta.total_teachers)          AS fact_total_teachers,
    ABS(SUM(mv.teacher_count) - MAX(ta.total_teachers)) AS rounding_diff
FROM uae.mv_uae_curriculum_kpi mv
JOIN (
    SELECT academic_year, region_en, education_type,
           SUM(teacher_count) AS total_teachers
    FROM uae.uae_fact_teachers_emirate
    GROUP BY 1, 2, 3
) ta USING (academic_year, region_en, education_type)
WHERE mv.has_teacher_data = TRUE
GROUP BY mv.academic_year, mv.region_en, mv.education_type
HAVING ABS(SUM(mv.teacher_count) - MAX(ta.total_teachers)) > 5
ORDER BY rounding_diff DESC;
*/

-- Check C : school totals in MV must exactly match uae_fact_schools
/*
SELECT
    mv.academic_year,
    mv.region_en,
    mv.education_type,
    SUM(mv.school_count)            AS mv_schools,
    MAX(sc.total_schools)           AS fact_schools,
    ABS(SUM(mv.school_count) - MAX(sc.total_schools)) AS diff
FROM uae.mv_uae_curriculum_kpi mv
JOIN (
    SELECT academic_year, region_en, education_type,
           SUM(school_count) AS total_schools
    FROM uae.uae_fact_schools
    GROUP BY 1, 2, 3
) sc USING (academic_year, region_en, education_type)
GROUP BY mv.academic_year, mv.region_en, mv.education_type
HAVING ABS(SUM(mv.school_count) - MAX(sc.total_schools)) > 0
ORDER BY diff DESC;
*/

-- Quick sanity check – should return rows for 2024-2025
-- SELECT * FROM uae.mv_uae_curriculum_kpi
-- WHERE academic_year = '2024-2025'
-- ORDER BY region_en, curriculum_en
-- LIMIT 30;

-- =============================================================================
-- 4.  REFRESH COMMAND  (add to cron or ETL pipeline)
-- =============================================================================
-- REFRESH MATERIALIZED VIEW CONCURRENTLY uae.mv_uae_curriculum_kpi;
-- Suggested schedule : nightly at 02:30 after ETL completes
-- Cron entry :
--   30 2 * * * psql -U tutorcloud_admin -d tutorcloud_db \
--     -c "REFRESH MATERIALIZED VIEW CONCURRENTLY uae.mv_uae_curriculum_kpi;" \
--     >> /var/log/tutorcloud_mv_refresh.log 2>&1

-- Unique index (required for REFRESH MATERIALIZED VIEW CONCURRENTLY)
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_curr_kpi_unique
    ON uae.mv_uae_curriculum_kpi (academic_year, region_en, education_type, curriculum_en);
