#!/usr/bin/env python3
from pathlib import Path
import re
import shutil

ROOT = Path("/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard")
LOADER = ROOT / "us_phase1_final_1a_load.py"
RENDERER = ROOT / "utils" / "us_page_renderer.py"

GEO_URL = "https://data-nces.opendata.arcgis.com/api/download/v1/items/a15e8731a17a46aabc452ea607f172c0/csv?layers=0"

def backup(path: Path, suffix: str):
    bak = path.with_name(path.name + suffix)
    if not bak.exists():
        shutil.copy2(path, bak)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str):
    path.write_text(text, encoding="utf-8")

def patch_loader():
    backup(LOADER, ".bak_build4_county_name")
    text = read(LOADER)

    if "GEO_URL =" not in text:
        m = re.search(r"TABLE_MAP\s*=\s*\{.*?\n\}", text, re.DOTALL)
        if not m:
            raise RuntimeError("Could not locate TABLE_MAP block in loader.")
        insert = (
            "\n\nGEO_URL = " + repr(GEO_URL) + "\n"
            "GEO_TABLE = f'stg_sch_geo_{YEAR_TAG}'\n"
            "TABLE_MAP['sch_geo'] = GEO_TABLE\n"
        )
        text = text[:m.end()] + insert + text[m.end():]

    old_stage_loop = """            for key, csv_path in extracted_csvs.items():
                log(f'Loading staging table for {key} ...')
                report['staging'][key] = load_stage_table(cur, key, csv_path)
                conn.commit()
"""
    new_stage_loop = """            for key, csv_path in extracted_csvs.items():
                log(f'Loading staging table for {key} ...')
                report['staging'][key] = load_stage_table(cur, key, csv_path)
                conn.commit()

            geo_target = dirs['raw'] / f'edge_public_school_locations_{YEAR_TAG}.csv'
            download(GEO_URL, geo_target)
            manifest['sch_geo'] = {'url': GEO_URL, 'path': str(geo_target), 'size_bytes': geo_target.stat().st_size}
            log('Loading staging table for sch_geo ...')
            report['staging']['sch_geo'] = load_stage_table(cur, 'sch_geo', geo_target)
            conn.commit()
"""
    if "Loading staging table for sch_geo" not in text:
        if old_stage_loop not in text:
            raise RuntimeError("Could not locate staging load loop in loader.")
        text = text.replace(old_stage_loop, new_stage_loop, 1)

    old_select = """        d.mcity AS city,
        d.mstate AS mailing_state,
        d.mzip AS zip_code,
        d.phone,
"""
    new_select = """        d.mcity AS city,
        d.mstate AS mailing_state,
        d.mzip AS zip_code,
        g.nmcnty AS county_name,
        d.phone,
"""
    if "AS county_name" not in text:
        if old_select not in text:
            raise RuntimeError("Could not locate dim_schools location select block.")
        text = text.replace(old_select, new_select, 1)

    old_join = """    FROM {SCHEMA}.{TABLE_MAP['sch_directory']} d
    LEFT JOIN {SCHEMA}.{TABLE_MAP['sch_characteristics']} c
      ON c.school_year = d.school_year AND c.ncessch = d.ncessch
    WHERE d.school_year = '{DASHBOARD_YEAR}';
"""
    new_join = """    FROM {SCHEMA}.{TABLE_MAP['sch_directory']} d
    LEFT JOIN {SCHEMA}.{TABLE_MAP['sch_characteristics']} c
      ON c.school_year = d.school_year AND c.ncessch = d.ncessch
    LEFT JOIN {SCHEMA}.{TABLE_MAP['sch_geo']} g
      ON BTRIM(COALESCE(g.ncessch::text, '')) = BTRIM(COALESCE(d.ncessch::text, ''))
    WHERE d.school_year = '{DASHBOARD_YEAR}';
"""
    if "TABLE_MAP['sch_geo']" in text and "LEFT JOIN {SCHEMA}.{TABLE_MAP['sch_geo']} g" not in text:
        if old_join not in text:
            raise RuntimeError("Could not locate dim_schools join block.")
        text = text.replace(old_join, new_join, 1)

    write(LOADER, text)
    print("Patched loader:", LOADER.name)

def patch_renderer():
    backup(RENDERER, ".bak_build4_county_name")
    text = read(RENDERER)

    old_warning = "County-level metrics are unavailable because the preserved NCES school directory staging table or county column could not be found."
    new_warning = "County-level metrics are unavailable because county_name is not yet populated in us.dim_schools for the selected data."
    text = text.replace(old_warning, new_warning)

    if "Build 4 county_name override" not in text:
        override = r'''

# ===== Build 4 county_name override =====
def _county_metric_frame(state_name: str = "All", school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    params: list = [school_year]
    clauses = [
        "ds.school_year = %s",
        "NULLIF(BTRIM(COALESCE(ds.county_name::text, '')), '') IS NOT NULL"
    ]
    if state_name and state_name != "All":
        clauses.append("ds.state_name = %s")
        params.append(state_name)

    county_expr = "COALESCE(NULLIF(BTRIM(ds.county_name::text), ''), 'Unknown')"
    location_expr = county_expr if state_name != "All" else f"{county_expr} || ', ' || ds.state_name"

    try:
        school_sum = _weighted_school_sum_raw("ds")
        student_sum = _weighted_students_sum_raw("ds", "f")
        teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    except Exception:
        school_sum = "COUNT(DISTINCT ds.school_id)"
        student_sum = "COALESCE(SUM(f.total_students), 0)"
        teacher_sum = "COALESCE(SUM(f.total_teachers), 0)"

    sql = f"""
    SELECT
        ds.state_name,
        {county_expr} AS county_name,
        {location_expr} AS location_name,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE {' AND '.join(clauses)}
    GROUP BY 1, 2, 3
    HAVING ROUND({school_sum}, 0) > 0
    ORDER BY total_schools DESC NULLS LAST, location_name
    """
    return _q(sql, params)
# ===== end Build 4 county_name override =====
'''
        text = text + "\n" + override

    write(RENDERER, text)
    print("Patched renderer:", RENDERER.name)

def main():
    patch_loader()
    patch_renderer()
    print("Build 4 county_name patch complete.")

if __name__ == "__main__":
    main()
