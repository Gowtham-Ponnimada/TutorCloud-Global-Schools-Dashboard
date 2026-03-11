-- ============================================================
-- CREATE UAE SCHEMA (mirrors india_2024_25 separation pattern)
-- ============================================================
CREATE SCHEMA IF NOT EXISTS uae;
SET search_path TO uae, public;

-- ============================================================
-- UAE DASHBOARD — PostgreSQL Schema DDL
-- TutorCloud Global Schools Dashboard
-- Generated: 2026-03-10
-- Run this FIRST before the ETL pipeline
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- DIMENSION: Emirates / Sub-Regions
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_dim_regions (
    region_id       SERIAL PRIMARY KEY,
    region_code     VARCHAR(10)  UNIQUE NOT NULL,
    region_name_en  VARCHAR(100) NOT NULL,
    region_name_ar  VARCHAR(100),
    emirate_en      VARCHAR(100),          -- parent emirate for sub-regions
    is_sub_region   BOOLEAN DEFAULT FALSE,
    display_order   INT
);

INSERT INTO uae_dim_regions (region_code, region_name_en, region_name_ar, emirate_en, is_sub_region, display_order)
VALUES
  ('AUH', 'ABU DHABI',         'أبوظبي',          'Abu Dhabi', FALSE, 1),
  ('AIN', 'AL AIN',            'العين',            'Abu Dhabi', TRUE,  2),
  ('DHF', 'AL DHAFRA',         'الظفرة',           'Abu Dhabi', TRUE,  3),
  ('DXB', 'DUBAI',             'دبي',              'Dubai',     FALSE, 4),
  ('SHJ', 'SHARJAH',           'الشارقة',          'Sharjah',   FALSE, 5),
  ('SHE', 'Sharjah / Eastern', 'الشارقة/المنطقة الشرقية', 'Sharjah', TRUE, 6),
  ('AJM', 'AJMAN',             'عجمان',            'Ajman',     FALSE, 7),
  ('UMQ', 'Umm Al Quwain',     'أم القيوين',       'UAQ',       FALSE, 8),
  ('RAK', 'Ras Al Khaimah',    'رأس الخيمة',       'RAK',       FALSE, 9),
  ('FUJ', 'AL FUJAIRAH',       'الفجيرة',          'Fujairah',  FALSE, 10)
ON CONFLICT (region_code) DO NOTHING;

-- ────────────────────────────────────────────────────────────
-- DIMENSION: Academic Years
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_dim_academic_years (
    year_id      SERIAL PRIMARY KEY,
    year_code    VARCHAR(10) UNIQUE NOT NULL,
    year_start   INT NOT NULL,
    year_end     INT NOT NULL,
    is_current   BOOLEAN DEFAULT FALSE
);

INSERT INTO uae_dim_academic_years (year_code, year_start, year_end, is_current)
VALUES
  ('2017-2018', 2017, 2018, FALSE),
  ('2018-2019', 2018, 2019, FALSE),
  ('2019-2020', 2019, 2020, FALSE),
  ('2020-2021', 2020, 2021, FALSE),
  ('2021-2022', 2021, 2022, FALSE),
  ('2022-2023', 2022, 2023, FALSE),
  ('2023-2024', 2023, 2024, FALSE),
  ('2024-2025', 2024, 2025, TRUE)
ON CONFLICT (year_code) DO NOTHING;

-- ────────────────────────────────────────────────────────────
-- FACT: Student Enrollment  (PRIMARY — 8,349 rows)
-- Source: Students_Enrolled_Public_Private.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_enrollment (
    id              BIGSERIAL PRIMARY KEY,
    academic_year   VARCHAR(10)  NOT NULL,
    region_en       VARCHAR(100) NOT NULL,
    education_type  VARCHAR(200),
    cycle           VARCHAR(30),
    grade           VARCHAR(50),
    gender          VARCHAR(20),
    nationality_cat VARCHAR(20),          -- 'Emirati' | 'Resident'
    student_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_enr_year    ON uae_fact_enrollment(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_enr_region  ON uae_fact_enrollment(region_en);
CREATE INDEX IF NOT EXISTS idx_uae_enr_type    ON uae_fact_enrollment(education_type);
CREATE INDEX IF NOT EXISTS idx_uae_enr_grade   ON uae_fact_enrollment(grade);

-- ────────────────────────────────────────────────────────────
-- FACT: Teachers & Staff by Emirate  (744 rows)
-- Source: Teachers_Admin_Gender_Nationality_Emirate.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_teachers_emirate (
    id              BIGSERIAL PRIMARY KEY,
    academic_year   VARCHAR(10)  NOT NULL,
    region_en       VARCHAR(100) NOT NULL,
    education_type  VARCHAR(200),
    gender          VARCHAR(20),
    nationality_cat VARCHAR(20),
    staff_count     INT NOT NULL DEFAULT 0,
    teacher_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_tch_year   ON uae_fact_teachers_emirate(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_tch_region ON uae_fact_teachers_emirate(region_en);

-- ────────────────────────────────────────────────────────────
-- FACT: Teachers by Subject Area  (6,002 rows)
-- Source: Number_of_Teachers_by_Subject.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_teachers_subject (
    id              BIGSERIAL PRIMARY KEY,
    academic_year   VARCHAR(10)  NOT NULL,
    region_en       VARCHAR(100) NOT NULL,
    education_type  VARCHAR(200),
    subject_en      VARCHAR(200),
    teacher_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_tsub_year    ON uae_fact_teachers_subject(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_tsub_region  ON uae_fact_teachers_subject(region_en);
CREATE INDEX IF NOT EXISTS idx_uae_tsub_subject ON uae_fact_teachers_subject(subject_en);

-- ────────────────────────────────────────────────────────────
-- FACT: Schools by Emirate, Curriculum & Gender  (495 rows)
-- Source: Schools_by_Emirate_Curriculum_Gender.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_schools (
    id              BIGSERIAL PRIMARY KEY,
    academic_year   VARCHAR(10)  NOT NULL,
    region_en       VARCHAR(100) NOT NULL,
    education_type  VARCHAR(200),
    curriculum_en   VARCHAR(200),
    student_gender  VARCHAR(20),          -- 'Boys' | 'Girls' | 'Co Edu'
    school_count    INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_sch_year   ON uae_fact_schools(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_sch_region ON uae_fact_schools(region_en);

-- ────────────────────────────────────────────────────────────
-- FACT: Pass & Fail Rates  (5,073 rows)
-- Source: Pass_and_Fail_Rates.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_pass_fail (
    id               BIGSERIAL PRIMARY KEY,
    academic_year    VARCHAR(10)  NOT NULL,
    region_en        VARCHAR(100) NOT NULL,
    education_type   VARCHAR(200),
    cycle            VARCHAR(30),
    grade            VARCHAR(50),
    gender           VARCHAR(20),
    nationality_cat  VARCHAR(20),         -- 'Emirati' | 'Expat'
    pass_percentage  NUMERIC(6,2),        -- stored as number e.g. 87.45
    student_count    INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_pf_year   ON uae_fact_pass_fail(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_pf_region ON uae_fact_pass_fail(region_en);
CREATE INDEX IF NOT EXISTS idx_uae_pf_grade  ON uae_fact_pass_fail(grade);

-- ────────────────────────────────────────────────────────────
-- FACT: Average Student Scores  (34,501 rows — LARGEST)
-- Source: Average_Student_Scores.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_student_scores (
    id               BIGSERIAL PRIMARY KEY,
    academic_year    VARCHAR(10)  NOT NULL,
    region_en        VARCHAR(100) NOT NULL,
    education_type   VARCHAR(200),
    cycle            VARCHAR(30),
    grade            VARCHAR(50),
    gender           VARCHAR(20),
    nationality_cat  VARCHAR(20),
    subject_en       VARCHAR(200),
    assessment_type  VARCHAR(50),
    student_count    INT NOT NULL DEFAULT 0,
    pass_percentage  NUMERIC(6,2),
    avg_score_band   VARCHAR(30),         -- '60 - 69.9', '70 - 79.9', etc.
    created_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_sc_year    ON uae_fact_student_scores(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_sc_region  ON uae_fact_student_scores(region_en);
CREATE INDEX IF NOT EXISTS idx_uae_sc_subject ON uae_fact_student_scores(subject_en);
CREATE INDEX IF NOT EXISTS idx_uae_sc_grade   ON uae_fact_student_scores(grade);
CREATE INDEX IF NOT EXISTS idx_uae_sc_yr_reg  ON uae_fact_student_scores(academic_year, region_en);

-- ────────────────────────────────────────────────────────────
-- FACT: Student Nationalities  (1,181 rows)
-- Source: GE_Students_Nationalities.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_student_nationalities (
    id               BIGSERIAL PRIMARY KEY,
    academic_year    VARCHAR(10) NOT NULL,
    nationality_en   VARCHAR(200),
    student_count    INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_uae_nat_year ON uae_fact_student_nationalities(academic_year);

-- ────────────────────────────────────────────────────────────
-- FACT: GE Teachers Summary  (42 rows — national level)
-- Source: GE_Teachers.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_ge_teachers (
    id               BIGSERIAL PRIMARY KEY,
    academic_year    INT NOT NULL,
    gender           VARCHAR(20),
    nationality      VARCHAR(20),
    total_teachers   INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────
-- FACT: GE Staff Summary  (117 rows — national level)
-- Source: GE_Staff.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_ge_staff (
    id               BIGSERIAL PRIMARY KEY,
    academic_year    INT NOT NULL,
    gender           VARCHAR(20),
    job_category     VARCHAR(100),
    nationality      VARCHAR(20),
    total_staff      INT NOT NULL DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────
-- FACT: GE Schools by Emirate  (161 rows — public + private UNION)
-- Source: GE_Public_Schools.csv + GE_Private_Schools.csv
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS uae_fact_ge_schools (
    id                   BIGSERIAL PRIMARY KEY,
    academic_year        VARCHAR(10)  NOT NULL,
    emirate_en           VARCHAR(100) NOT NULL,
    sector               VARCHAR(50),      -- 'Government' | 'Non Government'
    education_category   VARCHAR(100),
    school_count         INT NOT NULL DEFAULT 0,
    created_at           TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- MATERIALIZED VIEWS
-- ============================================================

-- MV 1: KPI Summary (top-row cards on dashboard)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_kpi_summary AS
SELECT
    e.academic_year,
    SUM(e.student_count)                                                              AS total_students,
    SUM(CASE WHEN e.nationality_cat = 'Emirati' THEN e.student_count ELSE 0 END)     AS emirati_students,
    SUM(CASE WHEN e.nationality_cat = 'Resident' THEN e.student_count ELSE 0 END)    AS resident_students,
    SUM(CASE WHEN e.gender = 'Female'  THEN e.student_count ELSE 0 END)              AS female_students,
    SUM(CASE WHEN e.gender = 'Male'    THEN e.student_count ELSE 0 END)              AS male_students,
    SUM(CASE WHEN e.education_type = 'Public' THEN e.student_count ELSE 0 END)       AS public_students,
    (SELECT SUM(s.school_count)   FROM uae_fact_schools s
     WHERE s.academic_year = e.academic_year)                                         AS total_schools,
    (SELECT SUM(t.teacher_count)  FROM uae_fact_teachers_emirate t
     WHERE t.academic_year = e.academic_year)                                         AS total_teachers,
    (SELECT SUM(t.staff_count)    FROM uae_fact_teachers_emirate t
     WHERE t.academic_year = e.academic_year)                                         AS total_staff,
    (SELECT COUNT(DISTINCT nationality_en) FROM uae_fact_student_nationalities n
     WHERE n.academic_year = e.academic_year)                                         AS unique_nationalities
FROM uae_fact_enrollment e
GROUP BY e.academic_year
ORDER BY e.academic_year DESC;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_uae_kpi_year ON mv_uae_kpi_summary(academic_year);

-- MV 2: Enrollment by Emirate & Year
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_enrollment_by_emirate AS
SELECT
    academic_year,
    region_en,
    SUM(student_count)                                                                AS total_students,
    SUM(CASE WHEN gender = 'Female'   THEN student_count ELSE 0 END)                 AS female_count,
    SUM(CASE WHEN gender = 'Male'     THEN student_count ELSE 0 END)                 AS male_count,
    SUM(CASE WHEN nationality_cat = 'Emirati'  THEN student_count ELSE 0 END)        AS emirati_count,
    SUM(CASE WHEN nationality_cat = 'Resident' THEN student_count ELSE 0 END)        AS resident_count,
    SUM(CASE WHEN education_type = 'Public' THEN student_count ELSE 0 END)           AS public_count,
    ROUND(SUM(CASE WHEN gender = 'Female' THEN student_count ELSE 0 END)
          * 100.0 / NULLIF(SUM(student_count), 0), 1)                                AS female_pct,
    ROUND(SUM(CASE WHEN nationality_cat = 'Emirati' THEN student_count ELSE 0 END)
          * 100.0 / NULLIF(SUM(student_count), 0), 1)                                AS emirati_pct
FROM uae_fact_enrollment
GROUP BY academic_year, region_en
ORDER BY academic_year DESC, total_students DESC;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_uae_enr_emirate ON mv_uae_enrollment_by_emirate(academic_year, region_en);

-- MV 3: Teachers by Emirate
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_teachers_by_emirate AS
SELECT
    academic_year,
    region_en,
    SUM(teacher_count)                                                                AS total_teachers,
    SUM(staff_count)                                                                  AS total_staff,
    SUM(CASE WHEN gender = 'Female' THEN teacher_count ELSE 0 END)                   AS female_teachers,
    SUM(CASE WHEN gender = 'Male'   THEN teacher_count ELSE 0 END)                   AS male_teachers,
    SUM(CASE WHEN nationality_cat = 'Emirati'  THEN teacher_count ELSE 0 END)        AS emirati_teachers,
    SUM(CASE WHEN nationality_cat = 'Resident' THEN teacher_count ELSE 0 END)        AS resident_teachers
FROM uae_fact_teachers_emirate
GROUP BY academic_year, region_en
ORDER BY academic_year DESC, total_teachers DESC;

CREATE UNIQUE INDEX IF NOT EXISTS uidx_uae_tch_emirate ON mv_uae_teachers_by_emirate(academic_year, region_en);

-- MV 4: Student-Teacher Ratio by Emirate
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_student_teacher_ratio AS
SELECT
    e.academic_year,
    e.region_en,
    e.total_students,
    t.total_teachers,
    ROUND(e.total_students::NUMERIC / NULLIF(t.total_teachers, 0), 1) AS ratio
FROM mv_uae_enrollment_by_emirate e
LEFT JOIN mv_uae_teachers_by_emirate t
       ON e.academic_year = t.academic_year
      AND UPPER(e.region_en) = UPPER(t.region_en)
ORDER BY e.academic_year DESC, ratio DESC;

-- MV 5: Pass Rate Trends
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_pass_rates AS
SELECT
    academic_year,
    region_en,
    cycle,
    gender,
    nationality_cat,
    ROUND(AVG(pass_percentage), 2)  AS avg_pass_rate,
    SUM(student_count)               AS total_students,
    COUNT(*)                         AS data_points
FROM uae_fact_pass_fail
GROUP BY academic_year, region_en, cycle, gender, nationality_cat
ORDER BY academic_year DESC, region_en;

-- MV 6: Schools by Curriculum
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_schools_curriculum AS
SELECT
    academic_year,
    region_en,
    curriculum_en,
    SUM(school_count)                                                                 AS total_schools,
    SUM(CASE WHEN student_gender = 'Girls'   THEN school_count ELSE 0 END)           AS girls_schools,
    SUM(CASE WHEN student_gender = 'Boys'    THEN school_count ELSE 0 END)           AS boys_schools,
    SUM(CASE WHEN student_gender = 'Co Edu'  THEN school_count ELSE 0 END)           AS coedu_schools
FROM uae_fact_schools
GROUP BY academic_year, region_en, curriculum_en
ORDER BY academic_year DESC, total_schools DESC;

-- MV 7: Top Subjects by Teacher Count
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_teachers_by_subject AS
SELECT
    academic_year,
    region_en,
    subject_en,
    SUM(teacher_count) AS total_teachers
FROM uae_fact_teachers_subject
WHERE subject_en IS NOT NULL
GROUP BY academic_year, region_en, subject_en
ORDER BY academic_year DESC, total_teachers DESC;

-- MV 8: Nationality Diversity
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_uae_nationality_diversity AS
SELECT
    academic_year,
    nationality_en,
    student_count,
    ROUND(student_count * 100.0 / SUM(student_count) OVER (PARTITION BY academic_year), 2) AS pct_of_total,
    RANK() OVER (PARTITION BY academic_year ORDER BY student_count DESC)                     AS rank_in_year
FROM uae_fact_student_nationalities
WHERE nationality_en IS NOT NULL
ORDER BY academic_year DESC, student_count DESC;

-- ============================================================
-- REFRESH ALL MVs  (run this after every ETL load)
-- ============================================================
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_kpi_summary;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_enrollment_by_emirate;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_teachers_by_emirate;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_student_teacher_ratio;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_pass_rates;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_schools_curriculum;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_teachers_by_subject;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_uae_nationality_diversity;

-- ============================================================
-- VERIFY  (run after DDL to confirm tables created)
-- ============================================================
-- SELECT table_name FROM information_schema.tables
--  WHERE table_schema = 'public' AND table_name LIKE 'uae_%'
--  ORDER BY table_name;
