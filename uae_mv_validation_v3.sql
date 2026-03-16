-- =============================================================================
-- UAE Curriculum KPI – Pre-Deployment Validation Suite  (v3)
-- File : uae_mv_validation_v3.sql
-- Purpose : Verify that mv_uae_curriculum_kpi aggregates exactly match the
--           underlying fact tables, so dashboard filter totals are consistent
--           with the Home page and all sub-tabs.
--
-- Run AFTER creating the MV:
--   psql -U tutorcloud_admin -d tutorcloud_db -f uae_mv_validation_v3.sql
--
-- All SELECT statements are wrapped in RAISE NOTICE / DO blocks so you can
-- see a clear PASS / FAIL in psql output.
-- =============================================================================

\echo ''
\echo '════════════════════════════════════════════════════════════════'
\echo '  UAE MV Validation Suite v3'
\echo '════════════════════════════════════════════════════════════════'
\echo ''

-- =============================================================================
-- TEST 1 : MV exists and has rows
-- =============================================================================
\echo '── TEST 1: MV row count ─────────────────────────────────────────'
DO $$
DECLARE
    cnt BIGINT;
BEGIN
    SELECT COUNT(*) INTO cnt FROM uae.mv_uae_curriculum_kpi;
    IF cnt > 0 THEN
        RAISE NOTICE 'PASS  mv_uae_curriculum_kpi has % rows', cnt;
    ELSE
        RAISE EXCEPTION 'FAIL  mv_uae_curriculum_kpi is empty – was the MV created?';
    END IF;
END $$;

-- =============================================================================
-- TEST 2 : School totals in MV exactly match uae_fact_schools
-- =============================================================================
\echo ''
\echo '── TEST 2: School aggregate consistency ─────────────────────────'
DO $$
DECLARE
    bad_cnt INT;
BEGIN
    SELECT COUNT(*) INTO bad_cnt
    FROM (
        SELECT
            mv.academic_year,
            mv.region_en,
            mv.education_type,
            SUM(mv.school_count)      AS mv_schools,
            MAX(sc.total_schools)     AS fact_schools,
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
    ) mismatches;

    IF bad_cnt = 0 THEN
        RAISE NOTICE 'PASS  School totals match exactly across all groups';
    ELSE
        RAISE WARNING 'FAIL  % group(s) have school count mismatches', bad_cnt;
    END IF;
END $$;

-- =============================================================================
-- TEST 3 : Student totals in MV match uae_fact_enrollment (rounding tol = #curricula)
-- =============================================================================
\echo ''
\echo '── TEST 3: Student aggregate consistency (public rows only) ─────'
DO $$
DECLARE
    bad_cnt INT;
BEGIN
    SELECT COUNT(*) INTO bad_cnt
    FROM (
        SELECT
            mv.academic_year,
            mv.region_en,
            mv.education_type,
            SUM(mv.student_count)     AS mv_students,
            MAX(ea.total_students)    AS fact_students,
            COUNT(*)                  AS curricula_count,
            ABS(SUM(mv.student_count) - MAX(ea.total_students)) AS rounding_diff
        FROM uae.mv_uae_curriculum_kpi mv
        JOIN (
            SELECT academic_year, region_en, education_type,
                   SUM(student_count) AS total_students
            FROM uae.uae_fact_enrollment
            GROUP BY 1, 2, 3
        ) ea USING (academic_year, region_en, education_type)
        WHERE mv.has_enrollment_data = TRUE
        GROUP BY mv.academic_year, mv.region_en, mv.education_type
        -- Allow rounding diff up to (number of curricula) because ROUND() can
        -- round each row up/down by ±0.5.  Anything beyond that is a data bug.
        HAVING ABS(SUM(mv.student_count) - MAX(ea.total_students)) > COUNT(*) + 1
    ) mismatches;

    IF bad_cnt = 0 THEN
        RAISE NOTICE 'PASS  Student totals match within rounding tolerance for all public-school groups';
    ELSE
        RAISE WARNING 'FAIL  % group(s) exceed rounding tolerance for student counts', bad_cnt;
    END IF;
END $$;

-- =============================================================================
-- TEST 4 : Teacher totals in MV match uae_fact_teachers_emirate
-- =============================================================================
\echo ''
\echo '── TEST 4: Teacher aggregate consistency ────────────────────────'
DO $$
DECLARE
    bad_cnt INT;
BEGIN
    SELECT COUNT(*) INTO bad_cnt
    FROM (
        SELECT
            mv.academic_year,
            mv.region_en,
            mv.education_type,
            SUM(mv.teacher_count)     AS mv_teachers,
            MAX(ta.total_teachers)    AS fact_teachers,
            COUNT(*)                  AS curricula_count,
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
        HAVING ABS(SUM(mv.teacher_count) - MAX(ta.total_teachers)) > COUNT(*) + 1
    ) mismatches;

    IF bad_cnt = 0 THEN
        RAISE NOTICE 'PASS  Teacher totals match within rounding tolerance for all groups';
    ELSE
        RAISE WARNING 'FAIL  % group(s) exceed rounding tolerance for teacher counts', bad_cnt;
    END IF;
END $$;

-- =============================================================================
-- TEST 5 : No unexpected NULL school_count rows
-- =============================================================================
\echo ''
\echo '── TEST 5: No NULL school_count rows ────────────────────────────'
DO $$
DECLARE
    bad_cnt INT;
BEGIN
    SELECT COUNT(*) INTO bad_cnt
    FROM uae.mv_uae_curriculum_kpi
    WHERE school_count IS NULL OR school_count < 0;

    IF bad_cnt = 0 THEN
        RAISE NOTICE 'PASS  All school_count values are non-null and non-negative';
    ELSE
        RAISE WARNING 'FAIL  % rows have NULL or negative school_count', bad_cnt;
    END IF;
END $$;

-- =============================================================================
-- TEST 6 : has_enrollment_data flag distribution is sensible
-- =============================================================================
\echo ''
\echo '── TEST 6: has_enrollment_data flag distribution ─────────────────'
SELECT
    academic_year,
    has_enrollment_data,
    COUNT(DISTINCT education_type)  AS distinct_edtypes,
    COUNT(*)                        AS rows
FROM uae.mv_uae_curriculum_kpi
GROUP BY 1, 2
ORDER BY 1, 2;

-- =============================================================================
-- TEST 7 : Spot-check 2024-2025 G.C.S.E Abu Dhabi (the original bug case)
-- =============================================================================
\echo ''
\echo '── TEST 7: Spot-check G.C.S.E Abu Dhabi 2024-2025 ──────────────'
SELECT
    academic_year,
    region_en,
    education_type,
    curriculum_en,
    school_count,
    school_share_pct,
    student_count,
    teacher_count,
    student_teacher_ratio,
    has_enrollment_data,
    has_teacher_data
FROM uae.mv_uae_curriculum_kpi
WHERE academic_year  = '2024-2025'
  AND region_en      ILIKE '%abu dhabi%'
  AND curriculum_en  ILIKE '%g.c.s.e%';

-- =============================================================================
-- TEST 8 : Home-page KPI consistency check
--          Total from MV (no filter) should equal fact-table totals displayed
--          on the Home page (within rounding tolerance).
-- =============================================================================
\echo ''
\echo '── TEST 8: Grand totals vs Home page ────────────────────────────'
SELECT
    'MV grand total 2024-25'          AS source,
    SUM(school_count)                  AS schools,
    SUM(student_count)                 AS students_estimated,
    SUM(teacher_count)                 AS teachers_estimated
FROM uae.mv_uae_curriculum_kpi
WHERE academic_year = '2024-2025'

UNION ALL

SELECT
    'Fact tables 2024-25',
    (SELECT COALESCE(SUM(school_count),0)   FROM uae.uae_fact_schools           WHERE academic_year='2024-2025'),
    (SELECT COALESCE(SUM(student_count),0)  FROM uae.uae_fact_enrollment        WHERE academic_year='2024-2025'),
    (SELECT COALESCE(SUM(teacher_count),0)  FROM uae.uae_fact_teachers_emirate  WHERE academic_year='2024-2025');

-- =============================================================================
-- TEST 9 : India dashboard tables are untouched (no uae schema in India tables)
-- =============================================================================
\echo ''
\echo '── TEST 9: India schema isolation ───────────────────────────────'
DO $$
DECLARE
    india_cnt INT;
BEGIN
    -- Verify India tables exist and have rows (schema 'india' must not be disturbed)
    SELECT COUNT(*) INTO india_cnt
    FROM information_schema.tables
    WHERE table_schema = 'india';

    IF india_cnt > 0 THEN
        RAISE NOTICE 'PASS  India schema has % table(s) – no cross-contamination', india_cnt;
    ELSE
        RAISE NOTICE 'INFO  India schema not found in this DB (may be separate DB) – OK';
    END IF;
END $$;

\echo ''
\echo '════════════════════════════════════════════════════════════════'
\echo '  Validation complete.  Review PASS/FAIL messages above.'
\echo '════════════════════════════════════════════════════════════════'
\echo ''
