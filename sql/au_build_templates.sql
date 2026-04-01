-- Australia build templates
-- These are reusable SQL templates referenced by the pseudocode.

-- 1) Clean profile
DROP TABLE IF EXISTS au.tmp_profile_clean;
CREATE TABLE au.tmp_profile_clean AS
SELECT
    load_id,
    NULLIF(BTRIM(calendar_year), '') AS calendar_year,
    NULLIF(BTRIM(acara_sml_id), '') AS acara_sml_id,
    NULLIF(BTRIM(location_age_id), '') AS location_age_id,
    NULLIF(BTRIM(school_age_id), '') AS school_age_id,
    NULLIF(BTRIM(school_name), '') AS school_name,
    NULLIF(BTRIM(suburb), '') AS suburb,
    NULLIF(BTRIM(state), '') AS state_abbr,
    NULLIF(BTRIM(postcode), '') AS postcode,
    NULLIF(BTRIM(school_sector), '') AS school_sector_raw,
    CASE
        WHEN NULLIF(BTRIM(school_sector), '') IN ('Government', 'G') THEN 'Government'
        WHEN NULLIF(BTRIM(school_sector), '') IN ('Catholic', 'C') THEN 'Catholic'
        WHEN NULLIF(BTRIM(school_sector), '') IN ('Independent', 'I') THEN 'Independent'
        ELSE NULL
    END AS management_type,
    NULLIF(BTRIM(school_type), '') AS school_type_raw,
    CASE
        WHEN NULLIF(BTRIM(school_type), '') = 'Primary' THEN 'Primary'
        WHEN NULLIF(BTRIM(school_type), '') = 'Secondary' THEN 'Secondary'
        WHEN NULLIF(BTRIM(school_type), '') = 'Combined' THEN 'Combined'
        WHEN NULLIF(BTRIM(school_type), '') = 'Special' THEN 'Special'
        ELSE NULL
    END AS school_level,
    NULLIF(BTRIM(campus_type), '') AS campus_type,
    NULLIF(BTRIM(rolled_reporting_description), '') AS reporting_model,
    NULLIF(BTRIM(school_url), '') AS school_url,
    NULLIF(BTRIM(governing_body), '') AS governing_body,
    NULLIF(BTRIM(governing_body_url), '') AS governing_body_url,
    NULLIF(BTRIM(year_range), '') AS year_range,
    NULLIF(BTRIM(geolocation), '') AS geolocation_label,
    NULLIF(BTRIM(icsea), '')::NUMERIC AS icsea,
    NULLIF(BTRIM(icsea_percentile), '')::NUMERIC AS icsea_percentile,
    NULLIF(BTRIM(sea_bottom_pct), '')::NUMERIC AS sea_bottom_pct,
    NULLIF(BTRIM(sea_lower_middle_pct), '')::NUMERIC AS sea_lower_middle_pct,
    NULLIF(BTRIM(sea_upper_middle_pct), '')::NUMERIC AS sea_upper_middle_pct,
    NULLIF(BTRIM(sea_top_pct), '')::NUMERIC AS sea_top_pct,
    NULLIF(BTRIM(teaching_staff), '')::NUMERIC AS teaching_staff,
    NULLIF(BTRIM(fte_teaching_staff), '')::NUMERIC AS fte_teaching_staff,
    NULLIF(BTRIM(non_teaching_staff), '')::NUMERIC AS non_teaching_staff,
    NULLIF(BTRIM(fte_non_teaching_staff), '')::NUMERIC AS fte_non_teaching_staff,
    CASE WHEN NULLIF(BTRIM(total_enrolments), '') ~ '^[0-9]+(\.[0-9]+)?$' THEN NULLIF(BTRIM(total_enrolments), '')::NUMERIC::INTEGER END AS total_students,
    CASE WHEN NULLIF(BTRIM(girls_enrolments), '') ~ '^[0-9]+(\.[0-9]+)?$' THEN NULLIF(BTRIM(girls_enrolments), '')::NUMERIC::INTEGER END AS girls_students,
    CASE WHEN NULLIF(BTRIM(boys_enrolments), '') ~ '^[0-9]+(\.[0-9]+)?$' THEN NULLIF(BTRIM(boys_enrolments), '')::NUMERIC::INTEGER END AS boys_students,
    NULLIF(BTRIM(fte_enrolments), '')::NUMERIC AS fte_students,
    NULLIF(BTRIM(indigenous_enrolments_pct), '')::NUMERIC AS indigenous_pct,
    NULLIF(BTRIM(lbote_yes_pct), '')::NUMERIC AS lbote_yes_pct,
    NULLIF(BTRIM(lbote_no_pct), '')::NUMERIC AS lbote_no_pct,
    NULLIF(BTRIM(lbote_not_stated_pct), '')::NUMERIC AS lbote_not_stated_pct
FROM au.stg_school_profile_2025;

-- 2) Clean location
DROP TABLE IF EXISTS au.tmp_location_clean;
CREATE TABLE au.tmp_location_clean AS
SELECT
    load_id,
    NULLIF(BTRIM(acara_sml_id), '') AS acara_sml_id,
    NULLIF(BTRIM(location_age_id), '') AS location_age_id,
    NULLIF(BTRIM(school_age_id), '') AS school_age_id,
    NULLIF(BTRIM(rolled_school_id), '') AS rolled_school_id,
    NULLIF(BTRIM(school_name), '') AS school_name,
    NULLIF(BTRIM(school_sector), '') AS school_sector_raw,
    NULLIF(BTRIM(school_type), '') AS school_type_raw,
    NULLIF(BTRIM(special_school), '') AS special_school,
    NULLIF(BTRIM(campus_type), '') AS campus_type,
    NULLIF(BTRIM(suburb), '') AS suburb,
    NULLIF(BTRIM(state), '') AS state_abbr,
    NULLIF(BTRIM(postcode), '') AS postcode,
    NULLIF(BTRIM(latitude), '')::NUMERIC AS latitude,
    NULLIF(BTRIM(longitude), '')::NUMERIC AS longitude,
    NULLIF(BTRIM(abs_remoteness_area), '') AS abs_remoteness_area,
    NULLIF(BTRIM(abs_remoteness_area_name), '') AS abs_remoteness_area_name,
    NULLIF(BTRIM(meshblock), '') AS meshblock,
    NULLIF(BTRIM(sa1_code), '') AS sa1_code,
    NULLIF(BTRIM(sa2_code), '') AS sa2_code,
    NULLIF(BTRIM(sa2_name), '') AS sa2_name,
    NULLIF(BTRIM(sa3_code), '') AS sa3_code,
    NULLIF(BTRIM(sa3_name), '') AS sa3_name,
    NULLIF(BTRIM(sa4_code), '') AS sa4_code,
    NULLIF(BTRIM(sa4_name), '') AS sa4_name,
    NULLIF(BTRIM(lga_code), '') AS lga_code,
    NULLIF(BTRIM(lga_name), '') AS lga_name,
    NULLIF(BTRIM(state_electoral_division_code), '') AS state_electoral_division_code,
    NULLIF(BTRIM(state_electoral_division_name), '') AS state_electoral_division_name,
    NULLIF(BTRIM(commonwealth_electoral_division_code), '') AS commonwealth_electoral_division_code,
    NULLIF(BTRIM(commonwealth_electoral_division_name), '') AS commonwealth_electoral_division_name
FROM au.stg_school_location_2025;

-- 3) Canonical rolled location
DROP TABLE IF EXISTS au.tmp_location_rolled_canonical;
CREATE TABLE au.tmp_location_rolled_canonical AS
SELECT *
FROM (
    SELECT
        lc.*,
        COALESCE(NULLIF(lc.rolled_school_id, ''), NULLIF(lc.acara_sml_id, ''), NULLIF(lc.school_age_id, '')) AS canonical_school_id,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(NULLIF(lc.rolled_school_id, ''), NULLIF(lc.acara_sml_id, ''), NULLIF(lc.school_age_id, ''))
            ORDER BY
                CASE
                    WHEN lc.campus_type ILIKE '%Single Entity%' THEN 1
                    WHEN lc.campus_type ILIKE '%Head Campus%' THEN 2
                    WHEN lc.campus_type ILIKE '%Sub-Campus%' THEN 3
                    ELSE 9
                END,
                lc.school_name
        ) AS rn
    FROM au.tmp_location_clean lc
) x
WHERE x.rn = 1;
