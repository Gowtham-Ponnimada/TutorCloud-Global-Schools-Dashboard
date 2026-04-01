-- =========================================================
-- Australia Dashboard Execution Pack
-- File: sql/au_schema.sql
-- Purpose: PostgreSQL DDL for Australia staging, marts, views
-- Canonical grain: rolled school reporting school-year
-- School year: 2025
-- =========================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS au;

-- ---------------------------------------------------------
-- 1. AUDIT + REFERENCE TABLES
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS au.audit_source_files (
    audit_id                     BIGSERIAL PRIMARY KEY,
    load_id                      TEXT NOT NULL,
    country_name                 TEXT NOT NULL DEFAULT 'Australia',
    school_year                  TEXT NOT NULL DEFAULT '2025',
    source_system                TEXT NOT NULL,
    source_file_name             TEXT NOT NULL,
    source_file_url              TEXT NOT NULL,
    source_sheet_name            TEXT,
    source_file_size_bytes       BIGINT,
    source_checksum              TEXT,
    source_last_modified         TEXT,
    row_count_loaded             BIGINT,
    notes                        TEXT,
    loaded_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS au.audit_reconciliation_2025 (
    recon_id                     BIGSERIAL PRIMARY KEY,
    load_id                      TEXT NOT NULL,
    country_name                 TEXT NOT NULL DEFAULT 'Australia',
    school_year                  TEXT NOT NULL DEFAULT '2025',
    metric_group                 TEXT NOT NULL,
    metric_name                  TEXT NOT NULL,
    source_a_name                TEXT NOT NULL,
    source_a_value               NUMERIC(18,4),
    source_b_name                TEXT NOT NULL,
    source_b_value               NUMERIC(18,4),
    absolute_delta               NUMERIC(18,4),
    pct_delta                    NUMERIC(18,6),
    status                       TEXT NOT NULL,
    notes                        TEXT,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS au.map_state_codes (
    state_abbr                   TEXT PRIMARY KEY,
    state_name                   TEXT NOT NULL,
    display_order                INTEGER NOT NULL
);

INSERT INTO au.map_state_codes (state_abbr, state_name, display_order) VALUES
('NSW', 'New South Wales', 1),
('VIC', 'Victoria', 2),
('QLD', 'Queensland', 3),
('WA',  'Western Australia', 4),
('SA',  'South Australia', 5),
('TAS', 'Tasmania', 6),
('ACT', 'Australian Capital Territory', 7),
('NT',  'Northern Territory', 8)
ON CONFLICT (state_abbr) DO NOTHING;

CREATE TABLE IF NOT EXISTS au.map_management_type (
    raw_value                    TEXT PRIMARY KEY,
    normalized_value             TEXT NOT NULL,
    display_order                INTEGER NOT NULL
);

INSERT INTO au.map_management_type (raw_value, normalized_value, display_order) VALUES
('Government', 'Government', 1),
('G',          'Government', 1),
('Catholic',   'Catholic',   2),
('C',          'Catholic',   2),
('Independent','Independent',3),
('I',          'Independent',3)
ON CONFLICT (raw_value) DO NOTHING;

CREATE TABLE IF NOT EXISTS au.map_school_level (
    raw_value                    TEXT PRIMARY KEY,
    normalized_value             TEXT NOT NULL,
    display_order                INTEGER NOT NULL
);

INSERT INTO au.map_school_level (raw_value, normalized_value, display_order) VALUES
('Primary',   'Primary',   1),
('Secondary', 'Secondary', 2),
('Combined',  'Combined',  3),
('Special',   'Special',   4)
ON CONFLICT (raw_value) DO NOTHING;

-- ---------------------------------------------------------
-- 2. STAGING TABLES
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS au.stg_school_profile_2025 (
    stg_profile_id                          BIGSERIAL PRIMARY KEY,
    load_id                                 TEXT NOT NULL,
    source_file_name                        TEXT NOT NULL,
    source_file_url                         TEXT NOT NULL,
    source_sheet_name                       TEXT NOT NULL DEFAULT 'SchoolProfile 2025',
    source_row_num                          INTEGER,
    calendar_year                           TEXT,
    acara_sml_id                            TEXT,
    location_age_id                         TEXT,
    school_age_id                           TEXT,
    school_name                             TEXT,
    suburb                                  TEXT,
    state                                   TEXT,
    postcode                                TEXT,
    school_sector                           TEXT,
    school_type                             TEXT,
    campus_type                             TEXT,
    rolled_reporting_description            TEXT,
    school_url                              TEXT,
    governing_body                          TEXT,
    governing_body_url                      TEXT,
    year_range                              TEXT,
    geolocation                             TEXT,
    icsea                                   TEXT,
    icsea_percentile                        TEXT,
    sea_bottom_pct                          TEXT,
    sea_lower_middle_pct                    TEXT,
    sea_upper_middle_pct                    TEXT,
    sea_top_pct                             TEXT,
    teaching_staff                          TEXT,
    fte_teaching_staff                      TEXT,
    non_teaching_staff                      TEXT,
    fte_non_teaching_staff                  TEXT,
    total_enrolments                        TEXT,
    girls_enrolments                        TEXT,
    boys_enrolments                         TEXT,
    fte_enrolments                          TEXT,
    indigenous_enrolments_pct               TEXT,
    lbote_yes_pct                           TEXT,
    lbote_no_pct                            TEXT,
    lbote_not_stated_pct                    TEXT,
    loaded_at                               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_au_stg_profile_load_id ON au.stg_school_profile_2025(load_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_profile_acara ON au.stg_school_profile_2025(acara_sml_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_profile_school_age ON au.stg_school_profile_2025(school_age_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_profile_state ON au.stg_school_profile_2025(state);

CREATE TABLE IF NOT EXISTS au.stg_school_location_2025 (
    stg_location_id                         BIGSERIAL PRIMARY KEY,
    load_id                                 TEXT NOT NULL,
    source_file_name                        TEXT NOT NULL,
    source_file_url                         TEXT NOT NULL,
    source_sheet_name                       TEXT NOT NULL DEFAULT 'SchoolLocations 2025',
    source_row_num                          INTEGER,
    calendar_year                           TEXT,
    acara_sml_id                            TEXT,
    location_age_id                         TEXT,
    school_age_id                           TEXT,
    rolled_school_id                        TEXT,
    school_name                             TEXT,
    school_sector                           TEXT,
    school_type                             TEXT,
    special_school                          TEXT,
    campus_type                             TEXT,
    suburb                                  TEXT,
    state                                   TEXT,
    postcode                                TEXT,
    latitude                                TEXT,
    longitude                               TEXT,
    abs_remoteness_area                     TEXT,
    abs_remoteness_area_name                TEXT,
    meshblock                               TEXT,
    sa1_code                                TEXT,
    sa2_code                                TEXT,
    sa2_name                                TEXT,
    sa3_code                                TEXT,
    sa3_name                                TEXT,
    sa4_code                                TEXT,
    sa4_name                                TEXT,
    lga_code                                TEXT,
    lga_name                                TEXT,
    state_electoral_division_code           TEXT,
    state_electoral_division_name           TEXT,
    commonwealth_electoral_division_code    TEXT,
    commonwealth_electoral_division_name    TEXT,
    loaded_at                               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_au_stg_location_load_id ON au.stg_school_location_2025(load_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_location_acara ON au.stg_school_location_2025(acara_sml_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_location_school_age ON au.stg_school_location_2025(school_age_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_location_rolled ON au.stg_school_location_2025(rolled_school_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_location_state ON au.stg_school_location_2025(state);

CREATE TABLE IF NOT EXISTS au.stg_enrolments_by_grade_2025 (
    stg_grade_id                            BIGSERIAL PRIMARY KEY,
    load_id                                 TEXT NOT NULL,
    source_file_name                        TEXT NOT NULL,
    source_file_url                         TEXT NOT NULL,
    source_sheet_name                       TEXT NOT NULL DEFAULT 'EnrolmentsByGrade 2025',
    source_row_num                          INTEGER,
    calendar_year                           TEXT,
    acara_sml_id                            TEXT,
    location_age_id                         TEXT,
    school_age_id                           TEXT,
    school_name                             TEXT,
    suburb                                  TEXT,
    state                                   TEXT,
    postcode                                TEXT,
    school_sector                           TEXT,
    school_type                             TEXT,
    campus_type                             TEXT,
    rolled_reporting_description            TEXT,
    pre_year1_2_offered                     TEXT,
    pre_year1_2_enrolments                  TEXT,
    pre_year1_1_offered                     TEXT,
    pre_year1_1_enrolments                  TEXT,
    year_1_offered                          TEXT,
    year_1_enrolments                       TEXT,
    year_2_offered                          TEXT,
    year_2_enrolments                       TEXT,
    year_3_offered                          TEXT,
    year_3_enrolments                       TEXT,
    year_4_offered                          TEXT,
    year_4_enrolments                       TEXT,
    year_5_offered                          TEXT,
    year_5_enrolments                       TEXT,
    year_6_offered                          TEXT,
    year_6_enrolments                       TEXT,
    year_7_offered                          TEXT,
    year_7_enrolments                       TEXT,
    year_8_offered                          TEXT,
    year_8_enrolments                       TEXT,
    year_9_offered                          TEXT,
    year_9_enrolments                       TEXT,
    year_10_offered                         TEXT,
    year_10_enrolments                      TEXT,
    year_11_offered                         TEXT,
    year_11_enrolments                      TEXT,
    year_12_offered                         TEXT,
    year_12_enrolments                      TEXT,
    primary_ungraded_offered                TEXT,
    primary_ungraded_enrolments             TEXT,
    secondary_ungraded_offered              TEXT,
    secondary_ungraded_enrolments           TEXT,
    total_enrolments                        TEXT,
    loaded_at                               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_au_stg_grade_load_id ON au.stg_enrolments_by_grade_2025(load_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_grade_acara ON au.stg_enrolments_by_grade_2025(acara_sml_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_grade_school_age ON au.stg_enrolments_by_grade_2025(school_age_id);
CREATE INDEX IF NOT EXISTS idx_au_stg_grade_state ON au.stg_enrolments_by_grade_2025(state);

-- ---------------------------------------------------------
-- 3. DIMENSIONS
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS au.dim_states (
    state_key                     BIGSERIAL PRIMARY KEY,
    country_name                  TEXT NOT NULL DEFAULT 'Australia',
    school_year                   TEXT NOT NULL DEFAULT '2025',
    state_abbr                    TEXT NOT NULL,
    state_name                    TEXT NOT NULL,
    display_order                 INTEGER NOT NULL,
    is_active                     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (school_year, state_abbr)
);

CREATE TABLE IF NOT EXISTS au.dim_districts (
    district_key                  BIGSERIAL PRIMARY KEY,
    country_name                  TEXT NOT NULL DEFAULT 'Australia',
    school_year                   TEXT NOT NULL DEFAULT '2025',
    state_abbr                    TEXT NOT NULL,
    state_name                    TEXT NOT NULL,
    district_id                   TEXT NOT NULL,
    district_name                 TEXT NOT NULL,
    district_type                 TEXT NOT NULL DEFAULT 'LGA',
    lga_code                      TEXT,
    source_system                 TEXT NOT NULL DEFAULT 'ACARA_School_Location_2025',
    school_count                  INTEGER,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (school_year, district_id)
);

CREATE INDEX IF NOT EXISTS idx_au_dim_districts_state ON au.dim_districts(school_year, state_abbr);
CREATE INDEX IF NOT EXISTS idx_au_dim_districts_name ON au.dim_districts(school_year, district_name);

CREATE TABLE IF NOT EXISTS au.dim_schools (
    school_key                                BIGSERIAL PRIMARY KEY,
    country_name                              TEXT NOT NULL DEFAULT 'Australia',
    school_year                               TEXT NOT NULL DEFAULT '2025',
    source_system                             TEXT NOT NULL DEFAULT 'ACARA_2025',
    source_school_year                        TEXT NOT NULL DEFAULT '2025',
    school_id                                 TEXT NOT NULL,
    acara_sml_id                              TEXT,
    rolled_school_id                          TEXT,
    location_age_id                           TEXT,
    school_age_id                             TEXT,
    school_name                               TEXT NOT NULL,
    state_abbr                                TEXT NOT NULL,
    state_name                                TEXT NOT NULL,
    district_id                               TEXT,
    district_name                             TEXT,
    district_type                             TEXT DEFAULT 'LGA',
    city_name                                 TEXT,
    suburb                                    TEXT,
    postcode                                  TEXT,
    lga_code                                  TEXT,
    lga_name                                  TEXT,
    abs_remoteness_area_code                  TEXT,
    abs_remoteness_area_name                  TEXT,
    sa1_code                                  TEXT,
    sa2_code                                  TEXT,
    sa2_name                                  TEXT,
    sa3_code                                  TEXT,
    sa3_name                                  TEXT,
    sa4_code                                  TEXT,
    sa4_name                                  TEXT,
    latitude                                  NUMERIC(12,8),
    longitude                                 NUMERIC(12,8),
    management_type                           TEXT,
    management_group                          TEXT,
    school_level                              TEXT,
    school_type_raw                           TEXT,
    campus_type                               TEXT,
    reporting_model                           TEXT,
    special_school_flag                       BOOLEAN,
    governing_body                            TEXT,
    governing_body_url                        TEXT,
    school_url                                TEXT,
    year_range                                TEXT,
    geolocation_label                         TEXT,
    icsea                                     NUMERIC(12,2),
    icsea_percentile                          NUMERIC(12,2),
    sea_bottom_pct                            NUMERIC(12,2),
    sea_lower_middle_pct                      NUMERIC(12,2),
    sea_upper_middle_pct                      NUMERIC(12,2),
    sea_top_pct                               NUMERIC(12,2),
    teaching_staff                            NUMERIC(12,2),
    fte_teaching_staff                        NUMERIC(12,2),
    non_teaching_staff                        NUMERIC(12,2),
    fte_non_teaching_staff                    NUMERIC(12,2),
    total_students                            INTEGER,
    girls_students                            INTEGER,
    boys_students                             INTEGER,
    fte_students                              NUMERIC(12,2),
    indigenous_pct                            NUMERIC(12,2),
    lbote_yes_pct                             NUMERIC(12,2),
    lbote_no_pct                              NUMERIC(12,2),
    lbote_not_stated_pct                      NUMERIC(12,2),
    student_teacher_ratio                     NUMERIC(12,4),
    data_quality_flag                         TEXT,
    is_reportable                             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (school_year, school_id)
);

CREATE INDEX IF NOT EXISTS idx_au_dim_schools_state ON au.dim_schools(school_year, state_abbr);
CREATE INDEX IF NOT EXISTS idx_au_dim_schools_district ON au.dim_schools(school_year, district_id);
CREATE INDEX IF NOT EXISTS idx_au_dim_schools_mgmt ON au.dim_schools(school_year, management_type);
CREATE INDEX IF NOT EXISTS idx_au_dim_schools_level ON au.dim_schools(school_year, school_level);
CREATE INDEX IF NOT EXISTS idx_au_dim_schools_suburb ON au.dim_schools(school_year, suburb);
CREATE INDEX IF NOT EXISTS idx_au_dim_schools_remoteness ON au.dim_schools(school_year, abs_remoteness_area_name);
CREATE INDEX IF NOT EXISTS idx_au_dim_schools_name ON au.dim_schools(school_year, school_name);

-- ---------------------------------------------------------
-- 4. FACT TABLES
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS au.fact_school_totals (
    fact_school_totals_id                       BIGSERIAL PRIMARY KEY,
    country_name                               TEXT NOT NULL DEFAULT 'Australia',
    school_year                                TEXT NOT NULL DEFAULT '2025',
    school_id                                  TEXT NOT NULL,
    source_system                              TEXT NOT NULL DEFAULT 'ACARA_2025',
    state_abbr                                 TEXT NOT NULL,
    district_id                                TEXT,
    management_type                            TEXT,
    school_level                               TEXT,
    total_students                             INTEGER,
    girls_students                             INTEGER,
    boys_students                              INTEGER,
    fte_students                               NUMERIC(12,2),
    teaching_staff                             NUMERIC(12,2),
    fte_teaching_staff                         NUMERIC(12,2),
    non_teaching_staff                         NUMERIC(12,2),
    fte_non_teaching_staff                     NUMERIC(12,2),
    student_teacher_ratio                      NUMERIC(12,4),
    indigenous_pct                             NUMERIC(12,2),
    lbote_yes_pct                              NUMERIC(12,2),
    lbote_no_pct                               NUMERIC(12,2),
    lbote_not_stated_pct                       NUMERIC(12,2),
    icsea                                      NUMERIC(12,2),
    icsea_percentile                           NUMERIC(12,2),
    sea_bottom_pct                             NUMERIC(12,2),
    sea_lower_middle_pct                       NUMERIC(12,2),
    sea_upper_middle_pct                       NUMERIC(12,2),
    sea_top_pct                                NUMERIC(12,2),
    created_at                                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (school_year, school_id)
);

CREATE INDEX IF NOT EXISTS idx_au_fact_school_totals_state ON au.fact_school_totals(school_year, state_abbr);
CREATE INDEX IF NOT EXISTS idx_au_fact_school_totals_district ON au.fact_school_totals(school_year, district_id);
CREATE INDEX IF NOT EXISTS idx_au_fact_school_totals_mgmt ON au.fact_school_totals(school_year, management_type);
CREATE INDEX IF NOT EXISTS idx_au_fact_school_totals_level ON au.fact_school_totals(school_year, school_level);

CREATE TABLE IF NOT EXISTS au.fact_grade_enrollment (
    fact_grade_enrollment_id                   BIGSERIAL PRIMARY KEY,
    country_name                               TEXT NOT NULL DEFAULT 'Australia',
    school_year                                TEXT NOT NULL DEFAULT '2025',
    school_id                                  TEXT NOT NULL,
    state_abbr                                 TEXT NOT NULL,
    district_id                                TEXT,
    management_type                            TEXT,
    school_level                               TEXT,
    source_system                              TEXT NOT NULL DEFAULT 'ACARA_2025',
    grade_code                                 TEXT NOT NULL,
    grade_label                                TEXT NOT NULL,
    grade_sort_order                           INTEGER NOT NULL,
    offered_flag                               BOOLEAN,
    enrolled_students                          INTEGER,
    suppressed_flag                            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (school_year, school_id, grade_code)
);

CREATE INDEX IF NOT EXISTS idx_au_fact_grade_state ON au.fact_grade_enrollment(school_year, state_abbr);
CREATE INDEX IF NOT EXISTS idx_au_fact_grade_district ON au.fact_grade_enrollment(school_year, district_id);
CREATE INDEX IF NOT EXISTS idx_au_fact_grade_code ON au.fact_grade_enrollment(school_year, grade_code);
CREATE INDEX IF NOT EXISTS idx_au_fact_grade_mgmt ON au.fact_grade_enrollment(school_year, management_type);

-- ---------------------------------------------------------
-- 5. VIEWS
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW au.vw_state_kpis_2025 AS
SELECT
    ds.school_year,
    ds.state_abbr,
    ds.state_name,
    COUNT(DISTINCT ds.school_id) AS schools,
    COALESCE(SUM(fs.total_students), 0) AS total_students,
    COALESCE(SUM(fs.girls_students), 0) AS girls_students,
    COALESCE(SUM(fs.boys_students), 0) AS boys_students,
    COALESCE(SUM(fs.fte_teaching_staff), 0) AS fte_teaching_staff,
    CASE
        WHEN COALESCE(SUM(fs.fte_teaching_staff), 0) > 0
        THEN ROUND(SUM(fs.total_students)::NUMERIC / SUM(fs.fte_teaching_staff), 4)
        ELSE NULL
    END AS student_teacher_ratio,
    CASE
        WHEN COALESCE(SUM(fs.total_students), 0) > 0
        THEN ROUND(SUM(fs.icsea * fs.total_students)::NUMERIC / SUM(fs.total_students), 2)
        ELSE NULL
    END AS weighted_avg_icsea,
    CASE
        WHEN COALESCE(SUM(fs.total_students), 0) > 0
        THEN ROUND(SUM(fs.indigenous_pct * fs.total_students)::NUMERIC / SUM(fs.total_students), 2)
        ELSE NULL
    END AS weighted_indigenous_pct,
    CASE
        WHEN COALESCE(SUM(fs.total_students), 0) > 0
        THEN ROUND(SUM(fs.lbote_yes_pct * fs.total_students)::NUMERIC / SUM(fs.total_students), 2)
        ELSE NULL
    END AS weighted_lbote_yes_pct
FROM au.dim_schools ds
LEFT JOIN au.fact_school_totals fs
  ON ds.school_year = fs.school_year
 AND ds.school_id   = fs.school_id
WHERE ds.school_year = '2025'
GROUP BY ds.school_year, ds.state_abbr, ds.state_name;

CREATE OR REPLACE VIEW au.vw_district_kpis_2025 AS
SELECT
    ds.school_year,
    ds.state_abbr,
    ds.state_name,
    ds.district_id,
    ds.district_name,
    COUNT(DISTINCT ds.school_id) AS schools,
    COALESCE(SUM(fs.total_students), 0) AS total_students,
    COALESCE(SUM(fs.girls_students), 0) AS girls_students,
    COALESCE(SUM(fs.boys_students), 0) AS boys_students,
    COALESCE(SUM(fs.fte_teaching_staff), 0) AS fte_teaching_staff,
    CASE
        WHEN COALESCE(SUM(fs.fte_teaching_staff), 0) > 0
        THEN ROUND(SUM(fs.total_students)::NUMERIC / SUM(fs.fte_teaching_staff), 4)
        ELSE NULL
    END AS student_teacher_ratio
FROM au.dim_schools ds
LEFT JOIN au.fact_school_totals fs
  ON ds.school_year = fs.school_year
 AND ds.school_id   = fs.school_id
WHERE ds.school_year = '2025'
GROUP BY ds.school_year, ds.state_abbr, ds.state_name, ds.district_id, ds.district_name;

CREATE OR REPLACE VIEW au.vw_dashboard_readiness AS
SELECT
    ds.school_year,
    COUNT(*) AS dim_school_rows,
    COUNT(*) FILTER (WHERE ds.school_id IS NOT NULL) AS school_id_present_rows,
    COUNT(*) FILTER (WHERE ds.district_name IS NOT NULL AND BTRIM(ds.district_name) <> '') AS district_present_rows,
    COUNT(*) FILTER (WHERE ds.suburb IS NOT NULL AND BTRIM(ds.suburb) <> '') AS suburb_present_rows,
    COUNT(*) FILTER (WHERE ds.latitude IS NOT NULL AND ds.longitude IS NOT NULL) AS geo_present_rows,
    COUNT(*) FILTER (WHERE ds.management_type IS NOT NULL AND BTRIM(ds.management_type) <> '') AS management_present_rows,
    COUNT(*) FILTER (WHERE ds.school_level IS NOT NULL AND BTRIM(ds.school_level) <> '') AS school_level_present_rows,
    COUNT(*) FILTER (WHERE fs.total_students IS NOT NULL) AS fact_total_students_present_rows
FROM au.dim_schools ds
LEFT JOIN au.fact_school_totals fs
  ON ds.school_year = fs.school_year
 AND ds.school_id   = fs.school_id
GROUP BY ds.school_year;

COMMIT;
