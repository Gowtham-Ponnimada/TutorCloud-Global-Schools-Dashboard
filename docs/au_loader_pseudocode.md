# Australia ETL Loader Pseudocode

## Purpose
This pseudocode defines the execution order for the Australia 2025 ETL using ACARA downloadable files as the row-level source and ABS 2025 as benchmark validation.

## Source files
- School Profile 2025.xlsx
- School Location 2025.xlsx
- Enrolments by Grade 2025.xlsx
- ABS Schools latest release (benchmark only)

---

## 1. Setup
```python
CONFIG = {
    'country_name': 'Australia',
    'school_year': '2025',
    'schema': 'au',
    'source_files': {
        'school_profile': {
            'url': 'https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/School%20Profile%202025.xlsx',
            'sheet': 'SchoolProfile 2025',
            'file_name': 'School Profile 2025.xlsx'
        },
        'school_location': {
            'url': 'https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/School%20Location%202025.xlsx',
            'sheet': 'SchoolLocations 2025',
            'file_name': 'School Location 2025.xlsx'
        },
        'enrolments_by_grade': {
            'url': 'https://dataandreporting.blob.core.windows.net/anrdataportal/Data-Access-Program/Enrolments%20by%20Grade%202025.xlsx',
            'sheet': 'EnrolmentsByGrade 2025',
            'file_name': 'Enrolments by Grade 2025.xlsx'
        }
    },
    'abs_benchmarks': {
        'total_students': 4160918,
        'government_students': 2613404,
        'catholic_students': 831692,
        'independent_students': 715822
    }
}
```

---

## 2. Main execution flow
```python
def main():
    load_id = make_load_id('au_2025')
    ensure_dirs([
        'data/au/final_2025/raw',
        'data/au/final_2025/extracted',
        'reports/au',
        'sql/au'
    ])

    conn = connect_db()
    execute_sql_file(conn, 'sql/au/au_schema.sql')

    # Step A: download files
    local_profile = download(CONFIG['source_files']['school_profile']['url'])
    local_location = download(CONFIG['source_files']['school_location']['url'])
    local_grade = download(CONFIG['source_files']['enrolments_by_grade']['url'])

    # Step B: validate worksheets
    assert_sheet_exists(local_profile, 'SchoolProfile 2025')
    assert_sheet_exists(local_profile, 'DataDictionary')
    assert_sheet_exists(local_location, 'SchoolLocations 2025')
    assert_sheet_exists(local_location, 'DataDictionary')
    assert_sheet_exists(local_grade, 'EnrolmentsByGrade 2025')
    assert_sheet_exists(local_grade, 'DataDictionary')

    # Step C: read workbooks
    df_profile = read_excel(local_profile, sheet_name='SchoolProfile 2025')
    df_location = read_excel(local_location, sheet_name='SchoolLocations 2025')
    df_grade = read_excel(local_grade, sheet_name='EnrolmentsByGrade 2025')

    # Step D: normalize columns and values
    df_profile = normalize_profile(df_profile)
    df_location = normalize_location(df_location)
    df_grade = normalize_grade(df_grade)

    # Step E: add audit metadata
    add_load_metadata(df_profile, load_id, CONFIG['source_files']['school_profile'])
    add_load_metadata(df_location, load_id, CONFIG['source_files']['school_location'])
    add_load_metadata(df_grade, load_id, CONFIG['source_files']['enrolments_by_grade'])

    # Step F: stage
    delete_existing_load(conn, load_id)
    bulk_load_dataframe(conn, 'au.stg_school_profile_2025', df_profile)
    bulk_load_dataframe(conn, 'au.stg_school_location_2025', df_location)
    bulk_load_dataframe(conn, 'au.stg_enrolments_by_grade_2025', df_grade)

    # Step G: build cleaned temp tables
    build_tmp_profile_clean(conn, load_id)
    build_tmp_location_clean(conn, load_id)
    build_tmp_location_rolled_canonical(conn, load_id)
    build_tmp_grade_wide_clean(conn, load_id)
    build_tmp_grade_long(conn, load_id)

    # Step H: build marts
    build_dim_states(conn)
    build_dim_districts(conn)
    build_dim_schools(conn)
    build_fact_school_totals(conn)
    build_fact_grade_enrollment(conn)
    build_views(conn)

    # Step I: QA and reconciliation
    qa = run_qa_checks(conn, load_id)
    reconciliation = run_abs_reconciliation(conn, load_id, CONFIG['abs_benchmarks'])

    # Step J: write report
    write_json_report({
        'load_id': load_id,
        'qa': qa,
        'reconciliation': reconciliation
    }, 'reports/au/au_phase1_final_load_report.json')

    conn.commit()
    conn.close()
```

---

## 3. Profile normalization
```python
def normalize_profile(df):
    df = rename_columns(df, {
        'Calendar Year': 'calendar_year',
        'ACARA SML ID': 'acara_sml_id',
        'Location AGE ID': 'location_age_id',
        'School AGE ID': 'school_age_id',
        'School Name': 'school_name',
        'Suburb': 'suburb',
        'State': 'state',
        'Postcode': 'postcode',
        'School Sector': 'school_sector',
        'School Type': 'school_type',
        'Campus Type': 'campus_type',
        'Rolled Reporting Description': 'rolled_reporting_description',
        'School URL': 'school_url',
        'Governing Body': 'governing_body',
        'Governing Body URL': 'governing_body_url',
        'Year Range': 'year_range',
        'Geolocation': 'geolocation',
        'ICSEA': 'icsea',
        'ICSEA Percentile': 'icsea_percentile',
        'Bottom SEA Quarter (%)': 'sea_bottom_pct',
        'Lower Middle SEA Quarter (%)': 'sea_lower_middle_pct',
        'Upper Middle SEA Quarter (%)': 'sea_upper_middle_pct',
        'Top SEA Quarter (%)': 'sea_top_pct',
        'Teaching Staff': 'teaching_staff',
        'Full Time Equivalent Teaching Staff': 'fte_teaching_staff',
        'Non-Teaching Staff': 'non_teaching_staff',
        'Full Time Equivalent Non-Teaching Staff': 'fte_non_teaching_staff',
        'Total Enrolments': 'total_enrolments',
        'Girls Enrolments': 'girls_enrolments',
        'Boys Enrolments': 'boys_enrolments',
        'Full Time Equivalent Enrolments': 'fte_enrolments',
        'Indigenous Enrolments (%)': 'indigenous_enrolments_pct',
        'Language Background Other Than English - Yes (%)': 'lbote_yes_pct',
        'Language Background Other Than English - No (%)': 'lbote_no_pct',
        'Language Background Other Than English - Not Stated (%)': 'lbote_not_stated_pct'
    })
    trim_all_strings(df)
    empty_to_null(df)
    cast_numeric_columns(df, [
        'icsea','icsea_percentile','sea_bottom_pct','sea_lower_middle_pct','sea_upper_middle_pct','sea_top_pct',
        'teaching_staff','fte_teaching_staff','non_teaching_staff','fte_non_teaching_staff','fte_enrolments',
        'indigenous_enrolments_pct','lbote_yes_pct','lbote_no_pct','lbote_not_stated_pct'
    ])
    cast_integer_columns(df, ['total_enrolments','girls_enrolments','boys_enrolments'])
    return df
```

---

## 4. Location normalization
```python
def normalize_location(df):
    df = rename_columns(df, {
        'Calendar Year': 'calendar_year',
        'ACARA SML ID': 'acara_sml_id',
        'Location AGE ID': 'location_age_id',
        'School AGE ID': 'school_age_id',
        'Rolled School ID': 'rolled_school_id',
        'School Name': 'school_name',
        'School Sector': 'school_sector',
        'School Type': 'school_type',
        'Special school': 'special_school',
        'Campus Type': 'campus_type',
        'Suburb': 'suburb',
        'State': 'state',
        'Postcode': 'postcode',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'ABS Remoteness Area': 'abs_remoteness_area',
        'ABS Remoteness Area Name': 'abs_remoteness_area_name',
        'Meshblock': 'meshblock',
        'Statistical Area 1': 'sa1_code',
        'Statistical Area 2': 'sa2_code',
        'Statistical Area 2 Name': 'sa2_name',
        'Statistical Area 3': 'sa3_code',
        'Statistical Area 3 Name': 'sa3_name',
        'Statistical Area 4': 'sa4_code',
        'Statistical Area 4 Name': 'sa4_name',
        'Local Government Area': 'lga_code',
        'Local Government Area Name': 'lga_name',
        'State Electoral Divisions': 'state_electoral_division_code',
        'State Electoral Divisions Name': 'state_electoral_division_name',
        'Commonwealth Electoral Divisions': 'commonwealth_electoral_division_code',
        'Commonwealth Electoral Divisions Name': 'commonwealth_electoral_division_name'
    })
    trim_all_strings(df)
    empty_to_null(df)
    cast_numeric_columns(df, ['latitude', 'longitude'])
    return df
```

---

## 5. Grade normalization
```python
def normalize_grade(df):
    df = rename_columns(df, {
        'Calendar Year': 'calendar_year',
        'ACARA SML ID': 'acara_sml_id',
        'Location AGE ID': 'location_age_id',
        'School AGE ID': 'school_age_id',
        'School Name': 'school_name',
        'Suburb': 'suburb',
        'State': 'state',
        'Postcode': 'postcode',
        'School Sector': 'school_sector',
        'School Type': 'school_type',
        'Campus Type': 'campus_type',
        'Rolled Reporting Description': 'rolled_reporting_description',
        'Two years before Year 1 Offered': 'pre_year1_2_offered',
        'Two years before Year 1 Enrolments': 'pre_year1_2_enrolments',
        'One year before Year 1 Offered': 'pre_year1_1_offered',
        'One year before Year 1 Enrolments': 'pre_year1_1_enrolments',
        'Year 1 Offered': 'year_1_offered',
        'Year 1 Enrolments': 'year_1_enrolments',
        'Year 2 Offered': 'year_2_offered',
        'Year 2 Enrolments': 'year_2_enrolments',
        'Year 3 Offered': 'year_3_offered',
        'Year 3 Enrolments': 'year_3_enrolments',
        'Year 4 Offered': 'year_4_offered',
        'Year 4 Enrolments': 'year_4_enrolments',
        'Year 5 Offered': 'year_5_offered',
        'Year 5 Enrolments': 'year_5_enrolments',
        'Year 6 Offered': 'year_6_offered',
        'Year 6 Enrolments': 'year_6_enrolments',
        'Year 7 Offered': 'year_7_offered',
        'Year 7 Enrolments': 'year_7_enrolments',
        'Year 8 Offered': 'year_8_offered',
        'Year 8 Enrolments': 'year_8_enrolments',
        'Year 9 Offered': 'year_9_offered',
        'Year 9 Enrolments': 'year_9_enrolments',
        'Year 10 Offered': 'year_10_offered',
        'Year 10 Enrolments': 'year_10_enrolments',
        'Year 11 Offered': 'year_11_offered',
        'Year 11 Enrolments': 'year_11_enrolments',
        'Year 12 Offered': 'year_12_offered',
        'Year 12 Enrolments': 'year_12_enrolments',
        'Primary Ungraded Offered': 'primary_ungraded_offered',
        'Primary Ungraded Enrolments': 'primary_ungraded_enrolments',
        'Secondary Ungraded Offered': 'secondary_ungraded_offered',
        'Secondary Ungraded Enrolments': 'secondary_ungraded_enrolments',
        'Total Enrolments': 'total_enrolments'
    })
    trim_all_strings(df)
    empty_to_null(df)
    cast_offered_flags(df)
    cast_grade_counts(df)
    return df
```

---

## 6. Canonical rolled-school location selection
```sql
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
```

---

## 7. Build dim_states
```sql
INSERT INTO au.dim_states (country_name, school_year, state_abbr, state_name, display_order, is_active)
SELECT
    'Australia',
    '2025',
    m.state_abbr,
    m.state_name,
    m.display_order,
    TRUE
FROM au.map_state_codes m
ON CONFLICT (school_year, state_abbr) DO UPDATE
SET state_name = EXCLUDED.state_name,
    display_order = EXCLUDED.display_order,
    is_active = EXCLUDED.is_active;
```

---

## 8. Build dim_districts
```sql
DELETE FROM au.dim_districts WHERE school_year = '2025';

INSERT INTO au.dim_districts (
    country_name, school_year, state_abbr, state_name,
    district_id, district_name, district_type, lga_code, source_system, school_count
)
SELECT
    'Australia',
    '2025',
    lc.state_abbr,
    sc.state_name,
    lc.state_abbr || ':' || COALESCE(NULLIF(lc.lga_code, ''), md5(lc.state_abbr || '|' || COALESCE(lc.lga_name, 'Unknown LGA'))),
    COALESCE(NULLIF(lc.lga_name, ''), 'Unknown LGA'),
    'LGA',
    lc.lga_code,
    'ACARA_School_Location_2025',
    COUNT(*)
FROM au.tmp_location_rolled_canonical lc
LEFT JOIN au.map_state_codes sc ON lc.state_abbr = sc.state_abbr
GROUP BY 1,2,3,4,5,6,7,8,9;
```

---

## 9. Build dim_schools
```sql
DELETE FROM au.dim_schools WHERE school_year = '2025';

INSERT INTO au.dim_schools (
    country_name, school_year, source_system, source_school_year,
    school_id, acara_sml_id, rolled_school_id, location_age_id, school_age_id,
    school_name, state_abbr, state_name,
    district_id, district_name, district_type,
    city_name, suburb, postcode, lga_code, lga_name,
    abs_remoteness_area_code, abs_remoteness_area_name,
    sa1_code, sa2_code, sa2_name, sa3_code, sa3_name, sa4_code, sa4_name,
    latitude, longitude,
    management_type, management_group, school_level, school_type_raw,
    campus_type, reporting_model, special_school_flag,
    governing_body, governing_body_url, school_url, year_range, geolocation_label,
    icsea, icsea_percentile, sea_bottom_pct, sea_lower_middle_pct, sea_upper_middle_pct, sea_top_pct,
    teaching_staff, fte_teaching_staff, non_teaching_staff, fte_non_teaching_staff,
    total_students, girls_students, boys_students, fte_students,
    indigenous_pct, lbote_yes_pct, lbote_no_pct, lbote_not_stated_pct,
    student_teacher_ratio, data_quality_flag, is_reportable
)
SELECT
    'Australia',
    '2025',
    'ACARA_2025',
    '2025',
    COALESCE(NULLIF(lc.rolled_school_id, ''), NULLIF(pc.acara_sml_id, ''), NULLIF(pc.school_age_id, '')) AS school_id,
    pc.acara_sml_id,
    lc.rolled_school_id,
    COALESCE(pc.location_age_id, lc.location_age_id),
    COALESCE(pc.school_age_id, lc.school_age_id),
    COALESCE(pc.school_name, lc.school_name) AS school_name,
    COALESCE(pc.state_abbr, lc.state_abbr) AS state_abbr,
    sc.state_name,
    COALESCE(pc.state_abbr, lc.state_abbr) || ':' || COALESCE(NULLIF(lc.lga_code, ''), md5(COALESCE(pc.state_abbr, lc.state_abbr) || '|' || COALESCE(lc.lga_name, 'Unknown LGA'))) AS district_id,
    COALESCE(NULLIF(lc.lga_name, ''), 'Unknown LGA') AS district_name,
    'LGA',
    lc.suburb,
    lc.suburb,
    COALESCE(pc.postcode, lc.postcode),
    lc.lga_code,
    lc.lga_name,
    lc.abs_remoteness_area,
    lc.abs_remoteness_area_name,
    lc.sa1_code,
    lc.sa2_code,
    lc.sa2_name,
    lc.sa3_code,
    lc.sa3_name,
    lc.sa4_code,
    lc.sa4_name,
    lc.latitude,
    lc.longitude,
    COALESCE(pc.management_type, CASE
        WHEN lc.school_sector_raw IN ('Government', 'G') THEN 'Government'
        WHEN lc.school_sector_raw IN ('Catholic', 'C') THEN 'Catholic'
        WHEN lc.school_sector_raw IN ('Independent', 'I') THEN 'Independent'
    END) AS management_type,
    COALESCE(pc.management_type, CASE
        WHEN lc.school_sector_raw IN ('Government', 'G') THEN 'Government'
        WHEN lc.school_sector_raw IN ('Catholic', 'C') THEN 'Catholic'
        WHEN lc.school_sector_raw IN ('Independent', 'I') THEN 'Independent'
    END) AS management_group,
    COALESCE(pc.school_level, CASE
        WHEN lc.school_type_raw = 'Primary' THEN 'Primary'
        WHEN lc.school_type_raw = 'Secondary' THEN 'Secondary'
        WHEN lc.school_type_raw = 'Combined' THEN 'Combined'
        WHEN lc.school_type_raw = 'Special' THEN 'Special'
    END) AS school_level,
    COALESCE(pc.school_type_raw, lc.school_type_raw) AS school_type_raw,
    COALESCE(pc.campus_type, lc.campus_type) AS campus_type,
    pc.reporting_model,
    CASE
        WHEN LOWER(COALESCE(lc.special_school, '')) IN ('yes', 'y', '1', 'true') THEN TRUE
        WHEN COALESCE(pc.school_level, lc.school_type_raw) = 'Special' THEN TRUE
        ELSE FALSE
    END AS special_school_flag,
    pc.governing_body,
    pc.governing_body_url,
    pc.school_url,
    pc.year_range,
    pc.geolocation_label,
    pc.icsea,
    pc.icsea_percentile,
    pc.sea_bottom_pct,
    pc.sea_lower_middle_pct,
    pc.sea_upper_middle_pct,
    pc.sea_top_pct,
    pc.teaching_staff,
    pc.fte_teaching_staff,
    pc.non_teaching_staff,
    pc.fte_non_teaching_staff,
    pc.total_students,
    pc.girls_students,
    pc.boys_students,
    pc.fte_students,
    pc.indigenous_pct,
    pc.lbote_yes_pct,
    pc.lbote_no_pct,
    pc.lbote_not_stated_pct,
    CASE WHEN COALESCE(pc.fte_teaching_staff, 0) > 0 THEN ROUND(pc.total_students::NUMERIC / pc.fte_teaching_staff, 4) END,
    CASE
        WHEN lc.latitude IS NULL OR lc.longitude IS NULL THEN 'MISSING_COORDINATES'
        WHEN lc.lga_name IS NULL OR BTRIM(lc.lga_name) = '' THEN 'MISSING_LGA'
        ELSE 'OK'
    END,
    TRUE
FROM au.tmp_profile_clean pc
LEFT JOIN au.tmp_location_rolled_canonical lc
  ON COALESCE(NULLIF(lc.rolled_school_id, ''), NULLIF(lc.acara_sml_id, ''), NULLIF(lc.school_age_id, ''))
   = COALESCE(NULLIF(pc.acara_sml_id, ''), NULLIF(pc.school_age_id, ''))
LEFT JOIN au.map_state_codes sc
  ON COALESCE(pc.state_abbr, lc.state_abbr) = sc.state_abbr;
```

---

## 10. Build fact_school_totals
```sql
DELETE FROM au.fact_school_totals WHERE school_year = '2025';

INSERT INTO au.fact_school_totals (
    country_name, school_year, school_id, source_system, state_abbr, district_id,
    management_type, school_level, total_students, girls_students, boys_students,
    fte_students, teaching_staff, fte_teaching_staff, non_teaching_staff, fte_non_teaching_staff,
    student_teacher_ratio, indigenous_pct, lbote_yes_pct, lbote_no_pct, lbote_not_stated_pct,
    icsea, icsea_percentile, sea_bottom_pct, sea_lower_middle_pct, sea_upper_middle_pct, sea_top_pct
)
SELECT
    country_name, school_year, school_id, source_system, state_abbr, district_id,
    management_type, school_level, total_students, girls_students, boys_students,
    fte_students, teaching_staff, fte_teaching_staff, non_teaching_staff, fte_non_teaching_staff,
    student_teacher_ratio, indigenous_pct, lbote_yes_pct, lbote_no_pct, lbote_not_stated_pct,
    icsea, icsea_percentile, sea_bottom_pct, sea_lower_middle_pct, sea_upper_middle_pct, sea_top_pct
FROM au.dim_schools
WHERE school_year = '2025';
```

---

## 11. Build fact_grade_enrollment
```sql
DELETE FROM au.fact_grade_enrollment WHERE school_year = '2025';

INSERT INTO au.fact_grade_enrollment (
    country_name, school_year, school_id, state_abbr, district_id,
    management_type, school_level, source_system,
    grade_code, grade_label, grade_sort_order,
    offered_flag, enrolled_students, suppressed_flag
)
SELECT
    'Australia',
    '2025',
    ds.school_id,
    ds.state_abbr,
    ds.district_id,
    ds.management_type,
    ds.school_level,
    'ACARA_2025',
    gl.grade_code,
    gl.grade_label,
    gl.grade_sort_order,
    gl.offered_flag,
    gl.enrolled_students,
    CASE WHEN gl.enrolled_students IS NULL AND gc.total_enrolments < 5 THEN TRUE ELSE FALSE END AS suppressed_flag
FROM au.tmp_grade_long gl
JOIN au.dim_schools ds
  ON ds.school_year = '2025'
 AND ds.school_id = COALESCE(NULLIF(gl.acara_sml_id, ''), NULLIF(gl.school_age_id, ''))
LEFT JOIN au.tmp_grade_wide_clean gc
  ON COALESCE(NULLIF(gl.acara_sml_id, ''), NULLIF(gl.school_age_id, ''))
   = COALESCE(NULLIF(gc.acara_sml_id, ''), NULLIF(gc.school_age_id, ''));
```

---

## 12. tmp_grade_long unpivot pattern
```python
def build_tmp_grade_long(conn, load_id):
    grade_specs = [
        ('PRE2', 'Two years before Year 1', 0, 'pre_year1_2_offered', 'pre_year1_2_enrolments'),
        ('PRE1', 'One year before Year 1', 1, 'pre_year1_1_offered', 'pre_year1_1_enrolments'),
        ('Y1', 'Year 1', 2, 'year_1_offered', 'year_1_enrolments'),
        ('Y2', 'Year 2', 3, 'year_2_offered', 'year_2_enrolments'),
        ('Y3', 'Year 3', 4, 'year_3_offered', 'year_3_enrolments'),
        ('Y4', 'Year 4', 5, 'year_4_offered', 'year_4_enrolments'),
        ('Y5', 'Year 5', 6, 'year_5_offered', 'year_5_enrolments'),
        ('Y6', 'Year 6', 7, 'year_6_offered', 'year_6_enrolments'),
        ('Y7', 'Year 7', 8, 'year_7_offered', 'year_7_enrolments'),
        ('Y8', 'Year 8', 9, 'year_8_offered', 'year_8_enrolments'),
        ('Y9', 'Year 9', 10, 'year_9_offered', 'year_9_enrolments'),
        ('Y10', 'Year 10', 11, 'year_10_offered', 'year_10_enrolments'),
        ('Y11', 'Year 11', 12, 'year_11_offered', 'year_11_enrolments'),
        ('Y12', 'Year 12', 13, 'year_12_offered', 'year_12_enrolments'),
        ('PUG', 'Primary Ungraded', 14, 'primary_ungraded_offered', 'primary_ungraded_enrolments'),
        ('SUG', 'Secondary Ungraded', 15, 'secondary_ungraded_offered', 'secondary_ungraded_enrolments')
    ]
    # Build insert-select UNION ALL SQL dynamically from grade_specs
```

---

## 13. QA checks
```sql
-- duplicate canonical school IDs
SELECT school_id, COUNT(*)
FROM au.dim_schools
WHERE school_year = '2025'
GROUP BY school_id
HAVING COUNT(*) > 1;

-- missing location coverage
SELECT
  COUNT(*) AS total_rows,
  COUNT(*) FILTER (WHERE latitude IS NOT NULL AND longitude IS NOT NULL) AS with_coordinates,
  COUNT(*) FILTER (WHERE district_name IS NOT NULL AND BTRIM(district_name) <> '') AS with_lga
FROM au.dim_schools
WHERE school_year = '2025';

-- management totals
SELECT management_type, SUM(total_students) AS students
FROM au.fact_school_totals
WHERE school_year = '2025'
GROUP BY management_type
ORDER BY students DESC;
```

---

## 14. ABS reconciliation
```sql
INSERT INTO au.audit_reconciliation_2025 (
    load_id, country_name, school_year, metric_group, metric_name,
    source_a_name, source_a_value, source_b_name, source_b_value,
    absolute_delta, pct_delta, status, notes
)
VALUES
(
    :load_id, 'Australia', '2025', 'national_students', 'total_students',
    'ACARA_derived', :actual_total, 'ABS_2025', 4160918,
    :actual_total - 4160918,
    CASE WHEN 4160918 <> 0 THEN (:actual_total - 4160918) / 4160918.0 END,
    CASE WHEN ABS(:actual_total - 4160918) <= 10000 THEN 'CHECK' ELSE 'REVIEW' END,
    'ABS used as benchmark only; ACARA row-level totals may differ because source scope differs.'
);
```

---

## 15. Run order in PuTTY
```bash
cd /path/to/repo
psql "$DATABASE_URL" -f sql/au_schema.sql
python3 au_phase1_final_load.py
python3 au_phase2_reconciliation.py
```
