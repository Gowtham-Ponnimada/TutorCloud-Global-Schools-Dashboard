#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen

import psycopg2
import py_compile

ROOT = Path("/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard")
SCHEMA = "us"
DASHBOARD_YEAR = "2024-2025"
PSS_SOURCE_YEAR = "2021-2022"
PSS_YEAR_TAG = "2021_2022"
PSS_URL = "https://nces.ed.gov/surveys/pss/zip/pss2122_pu_csv.zip"

RAW_DIR = ROOT / "data" / "us_pss" / "raw"
EXTRACT_DIR = ROOT / "data" / "us_pss" / "extracted"
REPORT_DIR = ROOT / "reports" / "us"

STAGE_TABLE = f"stg_pss_private_school_{PSS_YEAR_TAG}"
PRIVATE_DIM_TABLE = f"dim_private_schools_pss_{PSS_YEAR_TAG}"

def log(msg: str) -> None:
    print(msg, flush=True)

def sanitize(col: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(col).strip().lower()).strip("_")

def backup(path: Path, suffix: str) -> None:
    bak = path.with_name(path.name + suffix)
    if not bak.exists():
        shutil.copy2(path, bak)
        log(f"Backup created: {bak}")

def load_db_params() -> dict:
    params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "postgres")),
        "user": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres")),
        "password": os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
    }
    try:
        from utils.uae_page_renderer import _DB_PARAMS as UAE_DB_PARAMS
        params.update({
            "host": UAE_DB_PARAMS.get("host", params["host"]),
            "port": int(UAE_DB_PARAMS.get("port", params["port"])),
            "dbname": UAE_DB_PARAMS.get("dbname", params["dbname"]),
            "user": UAE_DB_PARAMS.get("user", params["user"]),
            "password": UAE_DB_PARAMS.get("password", params["password"]),
        })
    except Exception:
        pass
    return params

def table_columns(cur, table_name: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        [SCHEMA, table_name],
    )
    return [r[0] for r in cur.fetchall()]

def patch_loader_file() -> None:
    path = ROOT / "us_phase1_final_1a_load.py"
    text = path.read_text(encoding="utf-8")
    if "management_type" in text and "source_school_year" in text:
        log("Loader already patched.")
        return
    backup(path, ".bak_build2_private_management")
    old = """        END AS delivery_model,
        now() AS created_at"""
    new = """        END AS delivery_model,
        'Govt'::text AS management_type,
        'CCD'::text AS source_system,
        '2024-2025'::text AS source_school_year,
        now() AS created_at"""
    if old not in text:
        raise RuntimeError("Could not find loader delivery_model block")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    log("Patched us_phase1_final_1a_load.py")

def patch_renderer_file() -> None:
    path = ROOT / "utils" / "us_page_renderer.py"
    text = path.read_text(encoding="utf-8")
    backup(path, ".bak_build2_private_management")

    if "def _management_types(" not in text:
        anchor = '    return _distinct_values(sql, params, "delivery_model")\n'
        helper = """

def _management_types(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "management_type IS NOT NULL", "BTRIM(management_type) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT management_type FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY management_type"
    return _distinct_values(sql, params, "management_type")
"""
        if anchor not in text:
            raise RuntimeError("Could not find _delivery_models anchor")
        text = text.replace(anchor, anchor + helper, 1)

    old = '''        delivery_model = st.selectbox("School Type", delivery_opts, index=0, key="us_delivery_model")

        school_type_opts = _school_types(state, district)
'''
    new = '''        delivery_model = st.selectbox("School Type", delivery_opts, index=0, key="us_delivery_model")

        management_opts = ["All"] + _management_types(state, district)
        management_index = management_opts.index("Govt") if "Govt" in management_opts else 0
        management_type = st.selectbox("School Management", management_opts, index=management_index, key="us_management_type")

        school_type_opts = _school_types(state, district)
'''
    if old in text:
        text = text.replace(old, new, 1)

    old = '''            "delivery_model": delivery_model,
            "school_levels": school_levels,
'''
    new = '''            "delivery_model": delivery_model,
            "management_type": management_type,
            "school_levels": school_levels,
'''
    if old in text:
        text = text.replace(old, new, 1)

    old = '''    if delivery_model and delivery_model != "All":
        clauses.append(f"COALESCE({alias}.delivery_model, 'Unknown') = %s")
        params.append(delivery_model)
'''
    new = '''    if delivery_model and delivery_model != "All":
        clauses.append(f"COALESCE({alias}.delivery_model, 'Unknown') = %s")
        params.append(delivery_model)
    management_type = filters.get("management_type")
    if management_type and management_type != "All":
        clauses.append(f"COALESCE({alias}.management_type, 'Govt') = %s")
        params.append(management_type)
'''
    if old in text:
        text = text.replace(old, new, 1)
    old = '''        "Institution Type": ("ds.sch_type_text", "institution_type"),
        "District Type": ("dd.lea_type_text", "district_type"),
'''
    new = '''        "Institution Type": ("ds.sch_type_text", "institution_type"),
        "School Management": ("ds.management_type", "management_type"),
        "District Type": ("dd.lea_type_text", "district_type"),
'''
    if old in text:
        text = text.replace(old, new, 1)

    old = '        perf_delivery_model = st.selectbox("School Type", ["All"] + _delivery_models(perf_state), index=0, key="us_perf_delivery_model")\n        perf_filters = {"state": perf_state, "districts": [], "school_levels": [], "delivery_model": perf_delivery_model}\n'
    new = '        perf_delivery_model = st.selectbox("School Type", ["All"] + _delivery_models(perf_state), index=0, key="us_perf_delivery_model")\n        perf_management_opts = ["All"] + _management_types(perf_state)\n        perf_management_index = perf_management_opts.index("Govt") if "Govt" in perf_management_opts else 0\n        perf_management_type = st.selectbox("School Management", perf_management_opts, index=perf_management_index, key="us_perf_management_type")\n        perf_filters = {"state": perf_state, "districts": [], "school_levels": [], "delivery_model": perf_delivery_model, "management_type": perf_management_type}\n'
    if old in text:
        text = text.replace(old, new, 1)

    old = '        report_delivery_model = st.selectbox("Filter by School Type", ["All"] + _delivery_models(report_state), index=0, key="us_report_delivery_model")\n        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts")\n        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels")\n        report_filters = {\n            "state": report_state,\n            "delivery_model": report_delivery_model,\n            "districts": report_districts,\n            "school_levels": report_levels,\n        }\n'
    new = '        report_delivery_model = st.selectbox("Filter by School Type", ["All"] + _delivery_models(report_state), index=0, key="us_report_delivery_model")\n        report_management_opts = ["All"] + _management_types(report_state)\n        report_management_index = report_management_opts.index("Govt") if "Govt" in report_management_opts else 0\n        report_management_type = st.selectbox("Filter by School Management", report_management_opts, index=report_management_index, key="us_report_management_type")\n        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts")\n        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels")\n        report_filters = {\n            "state": report_state,\n            "delivery_model": report_delivery_model,\n            "management_type": report_management_type,\n            "districts": report_districts,\n            "school_levels": report_levels,\n        }\n'
    if old in text:
        text = text.replace(old, new, 1)

    state_sub = "    st.markdown(\"<div class='us-subtitle'>Comprehensive state-level analysis with advanced US-equivalent filters.</div>\", unsafe_allow_html=True)\n"
    state_note = state_sub + '    if filters.get("management_type") in ("All", "Private"):\n        st.info("School Management includes NCES PSS private-school data from 2021–2022. Public-school data remains CCD 2024–2025. Grade-level enrollment detail remains public-only for now.")\n'
    if state_sub in text and "private-school data from 2021–2022" not in text:
        text = text.replace(state_sub, state_note, 1)

    analytics_sub = "    st.markdown('<div class=\"sub-header\">Enhanced Analytics: Maps, Metrics, Comparison & Reports</div>', unsafe_allow_html=True)\n"
    analytics_note = analytics_sub + '    st.info("School Management defaults to Govt. Private-school rows use NCES PSS 2021–2022; public-school rows use CCD 2024–2025.")\n'
    if analytics_sub in text and "School Management defaults to Govt." not in text:
        text = text.replace(analytics_sub, analytics_note, 1)

    path.write_text(text, encoding="utf-8")
    log("Patched utils/us_page_renderer.py")

def download_pss_zip() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "pss2122_pu_csv.zip"
    if not zip_path.exists():
        log(f"Downloading {PSS_URL}")
        with urlopen(PSS_URL) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
    else:
        log(f"Using existing file: {zip_path.name}")
    return zip_path

def extract_pss_csv(zip_path: Path) -> Path:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_members:
            raise RuntimeError("No CSV found in PSS ZIP")
        member = csv_members[0]
        out = EXTRACT_DIR / Path(member).name
        if not out.exists():
            zf.extract(member, EXTRACT_DIR)
            extracted = EXTRACT_DIR / member
            if extracted != out:
                extracted.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(extracted), str(out))
        return out

def pick(headers: list[str], candidates: list[str]) -> str | None:
    hs = set(headers)
    for c in candidates:
        if c in hs:
            return c
    return None

def clean_num(v: str) -> str:
    s = "" if v is None else str(v).strip().replace(",", "")
    if s in ("", ".", "NA", "N/A", "NULL", "None"):
        return ""
    s = re.sub(r"[^0-9.\-]", "", s)
    return s

def title_clean(v: str, default: str = "") -> str:
    s = "" if v is None else str(v).strip()
    if not s:
        return default
    return re.sub(r"\s+", " ", s).title()

def normalize_level(raw: str) -> str:
    s = "" if raw is None else str(raw).strip().lower()
    if not s:
        return "Unknown"
    if "combined" in s or ("elementary" in s and ("secondary" in s or "high" in s)):
        return "Combined"
    if "elementary" in s:
        return "Elementary"
    if "secondary" in s or "high" in s:
        return "Secondary"
    if "pre" in s or "kindergarten" in s or "early" in s:
        return "Pre-K"
    return title_clean(raw, "Unknown")

def normalize_private_type(raw: str) -> str:
    return title_clean(raw, "Private School")

def write_normalized_csv(src_csv: Path, state_map: dict[str, tuple[str, str]]) -> Path:
    norm_path = EXTRACT_DIR / "pss_private_normalized_2021_2022.csv"
    last_err = None
    rows = None
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(src_csv, "r", newline="", encoding=enc) as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
                headers = [sanitize(h) for h in (reader.fieldnames or [])]
            break
        except Exception as e:
            last_err = e
            rows = None
    if rows is None:
        raise RuntimeError(f"Could not read PSS CSV: {last_err}")

    rows = [{sanitize(k): (v if v is not None else "") for k, v in row.items()} for row in rows]

    id_col = pick(headers, ["ppin", "school_id", "schoolid", "id"])
    name_col = pick(headers, ["pinst", "school_name", "school", "name"])
    city_col = pick(headers, ["pcity", "city"])
    state_col = pick(headers, ["pstabb", "state_abbr", "st", "state"])
    zip_col = pick(headers, ["pzip", "zip", "zip_code"])
    phone_col = pick(headers, ["pphone", "phone"])
    level_col = pick(headers, ["level", "school_level"])
    type_col = pick(headers, ["typology", "school_type", "private_school_type", "relig", "orientation"])
    students_col = pick(headers, ["numstuds", "enrollment", "student_count", "num_students"])
    teachers_col = pick(headers, ["numteach", "numteachers", "teacher_count", "teachers", "num_teachers"])
    weight_col = pick(headers, ["pfnlwt", "finalwt", "final_weight", "weight", "wgt"])

    if not name_col or not state_col:
        raise RuntimeError(f"PSS CSV missing required name/state columns. Headers sample: {headers[:50]}")

    out_fields = [
        "school_year","source_school_year","source_system","management_type",
        "school_id","school_name","state_fips","state_abbr","state_name",
        "district_id","district_name","city","zip_code","phone",
        "school_level","sch_type_text","delivery_model","pss_final_weight",
        "total_students","total_teachers","ptr"
    ]

    with open(norm_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for i, row in enumerate(rows, start=1):
            school_name = str(row.get(name_col, "")).strip()
            if not school_name:
                continue
            state_abbr = str(row.get(state_col, "")).strip().upper()
            state_name, state_fips = state_map.get(state_abbr, (state_abbr or "Unknown", ""))
            base_id = str(row.get(id_col, "")).strip() if id_col else ""
            school_id = "PSS-" + (base_id if base_id else f"{state_abbr or 'XX'}-{i}")
            district_id = f"PSS-{state_abbr or 'XX'}"
            district_name = f"{state_name} Private Schools" if state_name and state_name != "Unknown" else "Private Schools"
            total_students = clean_num(row.get(students_col, "")) if students_col else ""
            total_teachers = clean_num(row.get(teachers_col, "")) if teachers_col else ""
            pss_final_weight = clean_num(row.get(weight_col, "")) if weight_col else ""
            ptr = ""
            try:
                if total_students and total_teachers and float(total_teachers) > 0:
                    ptr = str(round(float(total_students) / float(total_teachers), 2))
            except Exception:
                ptr = ""
            w.writerow({
                "school_year": DASHBOARD_YEAR,
                "source_school_year": PSS_SOURCE_YEAR,
                "source_system": "PSS",
                "management_type": "Private",
                "school_id": school_id,
                "school_name": school_name,
                "state_fips": state_fips,
                "state_abbr": state_abbr,
                "state_name": state_name,
                "district_id": district_id,
                "district_name": district_name,
                "city": str(row.get(city_col, "")).strip() if city_col else "",
                "zip_code": str(row.get(zip_col, "")).strip() if zip_col else "",
                "phone": str(row.get(phone_col, "")).strip() if phone_col else "",
                "school_level": normalize_level(row.get(level_col, "")) if level_col else "Unknown",
                "sch_type_text": normalize_private_type(row.get(type_col, "")) if type_col else "Private School",
                "delivery_model": "Unknown",
                "pss_final_weight": pss_final_weight,
                "total_students": total_students,
                "total_teachers": total_teachers,
                "ptr": ptr,
            })
    return norm_path

def create_text_stage_and_load(cur, csv_path: Path) -> int:
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        headers = [sanitize(h) for h in next(csv.reader(f))]
    cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{STAGE_TABLE}")
    ddl = ", ".join([f'"{h}" TEXT' for h in headers])
    cur.execute(f"CREATE TABLE {SCHEMA}.{STAGE_TABLE} ({ddl})")
    cols = ", ".join([f'"{h}"' for h in headers])
    with open(csv_path, "r", encoding="utf-8") as f:
        cur.copy_expert(f"COPY {SCHEMA}.{STAGE_TABLE} ({cols}) FROM STDIN WITH CSV HEADER", f)
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{STAGE_TABLE}")
    return cur.fetchone()[0]

def build_private_dim(cur) -> int:
    cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{PRIVATE_DIM_TABLE}")
    cur.execute(f"""
        CREATE TABLE {SCHEMA}.{PRIVATE_DIM_TABLE} AS
        SELECT
            school_year, source_school_year, source_system, management_type,
            school_id, school_name, state_fips, state_abbr, state_name,
            district_id, district_name, city, zip_code, phone,
            school_level, sch_type_text, delivery_model,
            NULLIF(pss_final_weight, '')::numeric AS pss_final_weight,
            NULLIF(total_students, '')::numeric AS total_students,
            NULLIF(total_teachers, '')::numeric AS total_teachers,
            NULLIF(ptr, '')::numeric AS ptr
        FROM {SCHEMA}.{STAGE_TABLE}
    """)
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{PRIVATE_DIM_TABLE}")
    return int(cur.fetchone()[0])

def ensure_public_columns(cur):
    cur.execute(f"ALTER TABLE {SCHEMA}.dim_schools ADD COLUMN IF NOT EXISTS management_type text")
    cur.execute(f"ALTER TABLE {SCHEMA}.dim_schools ADD COLUMN IF NOT EXISTS source_system text")
    cur.execute(f"ALTER TABLE {SCHEMA}.dim_schools ADD COLUMN IF NOT EXISTS source_school_year text")
    cur.execute(f"ALTER TABLE {SCHEMA}.dim_schools ADD COLUMN IF NOT EXISTS pss_final_weight numeric")

    cur.execute(f"""
        UPDATE {SCHEMA}.dim_schools
           SET management_type = COALESCE(NULLIF(management_type, ''), 'Govt'),
               source_system = COALESCE(NULLIF(source_system, ''), 'CCD'),
               source_school_year = COALESCE(NULLIF(source_school_year, ''), '{DASHBOARD_YEAR}')
         WHERE COALESCE(source_system, 'CCD') <> 'PSS'
    """)

def refresh_private_dim_schools(cur) -> int:
    ensure_public_columns(cur)
    cur.execute(f"DELETE FROM {SCHEMA}.dim_schools WHERE COALESCE(source_system, '') = 'PSS' OR COALESCE(management_type, '') = 'Private'")
    cur.execute(f"""
        INSERT INTO {SCHEMA}.dim_schools (
            school_year, state_fips, state_name, state_abbr, district_id, state_district_id, district_name,
            school_id, state_school_id, schid, school_name, city, mailing_state, zip_code, phone, website,
            sy_status, sy_status_text, sch_type, sch_type_text, charter_text, school_level, low_grade, high_grade,
            igoffered, shared_time, nslp_status, nslp_status_text, virtual, virtual_text, delivery_model,
            management_type, source_system, source_school_year, pss_final_weight, created_at
        )
        SELECT
            school_year,
            state_fips,
            state_name,
            state_abbr,
            district_id,
            district_id AS state_district_id,
            district_name,
            school_id,
            school_id AS state_school_id,
            NULL AS schid,
            school_name,
            city,
            state_abbr AS mailing_state,
            zip_code,
            phone,
            NULL AS website,
            '1' AS sy_status,
            'Open' AS sy_status_text,
            NULL AS sch_type,
            sch_type_text,
            NULL AS charter_text,
            school_level,
            NULL AS low_grade,
            NULL AS high_grade,
            NULL AS igoffered,
            NULL AS shared_time,
            NULL AS nslp_status,
            NULL AS nslp_status_text,
            NULL AS virtual,
            NULL AS virtual_text,
            delivery_model,
            management_type,
            source_system,
            source_school_year,
            pss_final_weight,
            now() AS created_at
        FROM {SCHEMA}.{PRIVATE_DIM_TABLE}
    """)
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.dim_schools WHERE source_system = 'PSS'")
    return int(cur.fetchone()[0])

def refresh_private_fact_school_totals(cur) -> int:
    fact_cols = set(table_columns(cur, "fact_school_totals"))
    cur.execute(
        f"""
        DELETE FROM {SCHEMA}.fact_school_totals f
        USING {SCHEMA}.dim_schools ds
        WHERE ds.school_year = f.school_year
          AND ds.school_id = f.school_id
          AND COALESCE(ds.source_system, '') = 'PSS'
        """
    )
    ordered = [
        "school_year","school_id","total_students","total_teachers","ptr",
        "lunch_total","free_lunch_eligible","reduced_price_eligible","direct_certification",
        "free_lunch_qualified","reduced_price_qualified"
    ]
    expr = {
        "school_year": "school_year",
        "school_id": "school_id",
        "total_students": "total_students",
        "total_teachers": "total_teachers",
        "ptr": "ptr",
        "lunch_total": "NULL",
        "free_lunch_eligible": "NULL",
        "reduced_price_eligible": "NULL",
        "direct_certification": "NULL",
        "free_lunch_qualified": "NULL",
        "reduced_price_qualified": "NULL",
    }
    use_cols = [c for c in ordered if c in fact_cols]
    cur.execute(
        f"""
        INSERT INTO {SCHEMA}.fact_school_totals ({', '.join(use_cols)})
        SELECT {', '.join(expr[c] for c in use_cols)}
        FROM {SCHEMA}.{PRIVATE_DIM_TABLE}
        """
    )
    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM {SCHEMA}.fact_school_totals f
        JOIN {SCHEMA}.dim_schools ds
          ON ds.school_year = f.school_year
         AND ds.school_id = f.school_id
        WHERE COALESCE(ds.source_system, '') = 'PSS'
        """
    )
    return cur.fetchone()[0]

def refresh_private_dim_districts(cur) -> int:
    cols = set(table_columns(cur, "dim_districts"))
    if not cols:
        return 0
    cur.execute(
        f"""
        DELETE FROM {SCHEMA}.dim_districts
        WHERE district_id LIKE 'PSS-%'
           OR COALESCE(lea_type_text, '') = 'Private'
        """
    )
    ordered = ["school_year","state_fips","state_name","state_abbr","district_id","state_district_id","district_name","lea_type","lea_type_text","created_at"]
    expr = {
        "school_year": "school_year",
        "state_fips": "MIN(NULLIF(state_fips, ''))",
        "state_name": "state_name",
        "state_abbr": "state_abbr",
        "district_id": "district_id",
        "state_district_id": "district_id",
        "district_name": "district_name",
        "lea_type": "NULL",
        "lea_type_text": "'Private'",
        "created_at": "now()",
    }
    use_cols = [c for c in ordered if c in cols]
    cur.execute(
        f"""
        INSERT INTO {SCHEMA}.dim_districts ({', '.join(use_cols)})
        SELECT {', '.join(expr[c] for c in use_cols)}
        FROM {SCHEMA}.{PRIVATE_DIM_TABLE}
        GROUP BY school_year, state_name, state_abbr, district_id, district_name
        """
    )
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.dim_districts WHERE district_id LIKE 'PSS-%'")
    return cur.fetchone()[0]

def fetch_state_map(cur) -> dict[str, tuple[str, str]]:
    cur.execute(f"SELECT state_abbr, state_name, state_fips FROM {SCHEMA}.dim_states")
    out = {}
    for abbr, name, fips in cur.fetchall():
        if abbr:
            out[str(abbr).upper()] = (str(name), "" if fips is None else str(fips))
    return out

def main() -> None:
    patch_loader_file()
    patch_renderer_file()
    py_compile.compile(str(ROOT / "us_phase1_final_1a_load.py"), doraise=True)
    py_compile.compile(str(ROOT / "utils" / "us_page_renderer.py"), doraise=True)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = download_pss_zip()
    csv_path = extract_pss_csv(zip_path)

    conn = psycopg2.connect(**load_db_params())
    try:
        conn.autocommit = False
        cur = conn.cursor()
        state_map = fetch_state_map(cur)
        norm_csv = write_normalized_csv(csv_path, state_map)
        stage_rows = create_text_stage_and_load(cur, norm_csv)
        private_dim_rows = build_private_dim(cur)
        ensure_public_columns(cur)
        private_school_rows = refresh_private_dim_schools(cur)
        private_fact_rows = refresh_private_fact_school_totals(cur)
        private_district_rows = refresh_private_dim_districts(cur)
        conn.commit()

        cur.execute(
            f"""
            SELECT management_type, COALESCE(source_system, 'UNKNOWN') AS source_system, COUNT(*)
            FROM {SCHEMA}.dim_schools
            WHERE school_year = %s
            GROUP BY 1,2
            ORDER BY 1,2
            """,
            [DASHBOARD_YEAR],
        )
        mgmt = cur.fetchall()

        report = {
            "pss_url": PSS_URL,
            "pss_source_year": PSS_SOURCE_YEAR,
            "dashboard_year": DASHBOARD_YEAR,
            "stage_table": STAGE_TABLE,
            "private_dim_table": PRIVATE_DIM_TABLE,
            "stage_rows": stage_rows,
            "private_dim_rows": private_dim_rows,
            "private_school_rows_in_dim_schools": private_school_rows,
            "private_school_rows_in_fact_school_totals": private_fact_rows,
            "private_synthetic_district_rows": private_district_rows,
            "management_distribution": mgmt,
        }
        out = REPORT_DIR / "us_build2_private_pss_management_report.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        log(json.dumps(report, indent=2))
        log(f"Report written to: {out}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
