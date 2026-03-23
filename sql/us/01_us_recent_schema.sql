CREATE SCHEMA IF NOT EXISTS us;

DROP TABLE IF EXISTS us.dim_states CASCADE;
DROP TABLE IF EXISTS us.dim_districts CASCADE;
DROP TABLE IF EXISTS us.dim_schools CASCADE;
DROP TABLE IF EXISTS us.fact_enrollment CASCADE;
DROP TABLE IF EXISTS us.fact_staff CASCADE;
DROP TABLE IF EXISTS us.fact_school_characteristics CASCADE;
DROP TABLE IF EXISTS us.fact_performance_state CASCADE;

CREATE TABLE us.dim_states (
    school_year      text,
    state_name       text,
    state_abbr       text,
    school_count     bigint DEFAULT 0,
    district_count   bigint DEFAULT 0,
    created_at       timestamp DEFAULT now()
);

CREATE TABLE us.dim_districts (
    school_year      text,
    district_id      text,
    district_name    text,
    state_name       text,
    state_abbr       text,
    city             text,
    zip_code         text,
    phone            text,
    source_file      text,
    created_at       timestamp DEFAULT now()
);

CREATE TABLE us.dim_schools (
    school_year        text,
    school_id          text,
    school_name        text,
    district_id        text,
    district_name      text,
    state_name         text,
    state_abbr         text,
    city               text,
    county_name        text,
    zip_code           text,
    locale             text,
    school_type        text,
    school_level       text,
    low_grade          text,
    high_grade         text,
    charter_status     text,
    operational_status text,
    latitude           text,
    longitude          text,
    source_file        text,
    created_at         timestamp DEFAULT now()
);

CREATE TABLE us.fact_enrollment (
    school_year      text,
    state_name       text,
    state_abbr       text,
    district_id      text,
    district_name    text,
    school_id        text,
    school_name      text,
    sex              text,
    race_ethnicity   text,
    grade_level      text,
    student_count    numeric,
    source_file      text,
    created_at       timestamp DEFAULT now()
);

CREATE TABLE us.fact_staff (
    school_year      text,
    state_name       text,
    state_abbr       text,
    district_id      text,
    district_name    text,
    school_id        text,
    school_name      text,
    staff_category   text,
    teacher_fte      numeric,
    staff_fte        numeric,
    source_file      text,
    created_at       timestamp DEFAULT now()
);

CREATE TABLE us.fact_school_characteristics (
    school_year           text,
    state_name            text,
    state_abbr            text,
    district_id           text,
    district_name         text,
    school_id             text,
    school_name           text,
    frpl_eligible         numeric,
    characteristic_name   text,
    characteristic_value  text,
    source_file           text,
    created_at            timestamp DEFAULT now()
);

CREATE TABLE us.fact_performance_state (
    school_year      text,
    state_name       text,
    state_abbr       text,
    subject          text,
    grade_level      text,
    average_score    numeric,
    proficiency_pct  numeric,
    source_file      text,
    created_at       timestamp DEFAULT now()
);

CREATE INDEX idx_us_dim_states_year_state ON us.dim_states (school_year, state_name);
CREATE INDEX idx_us_dim_districts_year_state ON us.dim_districts (school_year, state_name);
CREATE INDEX idx_us_dim_districts_district ON us.dim_districts (district_id);
CREATE INDEX idx_us_dim_schools_year_state ON us.dim_schools (school_year, state_name);
CREATE INDEX idx_us_dim_schools_district ON us.dim_schools (district_id);
CREATE INDEX idx_us_dim_schools_school ON us.dim_schools (school_id);
