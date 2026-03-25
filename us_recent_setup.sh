#!/usr/bin/env bash
set -euo pipefail

REPO="/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard"
cd "$REPO"

if [ -x "$REPO/venv/bin/python" ]; then
  PY="$REPO/venv/bin/python"
  PIP="$REPO/venv/bin/pip"
else
  PY="python3"
  PIP="pip3"
fi

echo "==> Cleaning any broken partial US setup files"
rm -f "$REPO/sql/us/01_us_recent_schema.sql" || true
rm -f "$REPO/sql/us/02_us_recent_views.sql" || true
rm -f "$REPO/scripts/us/load_recent_us_nces.py" || true
rm -f "$REPO/scripts/us/validate_recent_us_schema.py" || true
rm -f "$REPO/scripts/us/patch_us_routing.py" || true
rm -f "$REPO/utils/us_page_renderer.py" || true

echo "==> Creating repo structure"
mkdir -p "$REPO/data/us/raw/2023_2024"
mkdir -p "$REPO/data/us/raw/2024_2025_prelim"
mkdir -p "$REPO/data/us/extracted/2023_2024"
mkdir -p "$REPO/data/us/extracted/2024_2025_prelim"
mkdir -p "$REPO/data/us/manual_drop"
mkdir -p "$REPO/data/us/docs"
mkdir -p "$REPO/scripts/us"
mkdir -p "$REPO/sql/us"
mkdir -p "$REPO/reports/us"
mkdir -p "$REPO/utils"

cat > "$REPO/data/us/.gitignore" <<'EOF'
raw/
extracted/
manual_drop/*
!manual_drop/.gitkeep
EOF

touch "$REPO/data/us/manual_drop/.gitkeep"

cat > "$REPO/reports/us/.gitignore" <<'EOF'
*
!.gitignore
EOF

echo "==> Writing SQL schema"
cat > "$REPO/sql/us/01_us_recent_schema.sql" <<'SQLEOF'
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
SQLEOF

cat > "$REPO/sql/us/02_us_recent_views.sql" <<'SQLEOF'
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
SQLEOF

echo "==> Writing loader script"
cat > "$REPO/scripts/us/load_recent_us_nces.py" <<'PYEOF'
from __future__ import annotations

import json
import os
import re
import sys
import zipfile
import urllib.request
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import psycopg2
from sqlalchemy import create_engine

REPO = Path(__file__).resolve().parents[2]
RAW_2324 = REPO / "data/us/raw/2023_2024"
RAW_2425 = REPO / "data/us/raw/2024_2025_prelim"
EXT_2324 = REPO / "data/us/extracted/2023_2024"
EXT_2425 = REPO / "data/us/extracted/2024_2025_prelim"
REPORT_DIR = REPO / "reports/us"
SQL_DIR = REPO / "sql/us"

URLS = {
    "schools_2324": "https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2324_w_0a_050824.zip",
    "schools_2324_docs": "https://nces.ed.gov/ccd/Data/zip/2023-24_Sch_Documentation_prelim.zip",
    "lea_2324": "https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2324_w_0a_050824.zip",
    "lea_2324_docs": "https://nces.ed.gov/ccd/Data/zip/2023-24_Lea_Documentation_prelim.zip",
    "schools_2425": "https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_0a_051425.zip",
    "schools_2425_docs": "https://nces.ed.gov/ccd/Data/zip/2024-25_Sch_Documentation_prelim.zip",
    "lea_2425": "https://nces.ed.gov/ccd/Data/zip/ccd_lea_029_2425_w_0a_051425.zip",
    "lea_2425_docs": "https://nces.ed.gov/ccd/Data/zip/2024-25_Lea_Documentation_prelim.zip",
}

STATE_ABBR_TO_NAME = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut",
    "DE":"Delaware","DC":"District of Columbia","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
    "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland",
    "MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana",
    "NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
    "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania",
    "RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah",
    "VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
    "PR":"Puerto Rico","GU":"Guam","VI":"Virgin Islands","AS":"American Samoa","MP":"Northern Mariana Islands",
    "DO":"Department of Defense","BI":"Bureau of Indian Education"
}

def load_db_config():
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", os.getenv("DB_DATABASE", "tutorcloud_db")),
        "user": os.getenv("DB_USER", "tutorcloud_admin"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    try:
        sys.path.insert(0, str(REPO))
        from utils.uae_page_renderer import DB_CONFIG as UAE_DB_CONFIG  # type: ignore
        if isinstance(UAE_DB_CONFIG, dict):
            for k in ("host", "port", "dbname", "user", "password"):
                if UAE_DB_CONFIG.get(k) not in (None, ""):
                    cfg[k] = UAE_DB_CONFIG[k]
    except Exception:
        pass
    return cfg

DB = load_db_config()

def engine():
    url = (
        f"postgresql+psycopg2://{quote_plus(str(DB['user']))}:{quote_plus(str(DB['password']))}"
        f"@{DB['host']}:{DB['port']}/{DB['dbname']}"
    )
    return create_engine(url, future=True)

def conn():
    return psycopg2.connect(**DB)

def run_sql_file(path: Path):
    sql = path.read_text(encoding="utf-8")
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql)
        c.commit()

def sanitize_columns(cols):
    seen = {}
    out = []
    for c in cols:
        x = re.sub(r"[^a-zA-Z0-9]+", "_", str(c).strip().lower()).strip("_")
        if not x:
            x = "col"
        if x[0].isdigit():
            x = f"c_{x}"
        n = seen.get(x, 0)
        if n:
            seen[x] = n + 1
            out.append(f"{x}_{n+1}")
        else:
            seen[x] = 1
            out.append(x)
    return out

def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, dest)

def extract_zip(zip_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = out_dir / f".done_{zip_path.stem}"
    if marker.exists():
        return
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
    marker.write_text(datetime.utcnow().isoformat(), encoding="utf-8")

def choose_flat_file(root: Path):
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".txt", ".dat"}]
    if not files:
        return None
    def score(p: Path):
        name = p.name.lower()
        ext_rank = 0 if p.suffix.lower() == ".csv" else 1
        doc_penalty = 100 if any(x in name for x in ["layout", "note", "documentation", "companion", "format"]) else 0
        return (doc_penalty, ext_rank, -p.stat().st_size)
    return sorted(files, key=score)[0]

def read_any(path: Path) -> pd.DataFrame:
    attempts = [
        dict(sep=None, engine="python", dtype=str, encoding="latin1", on_bad_lines="skip"),
        dict(sep=",", engine="python", dtype=str, encoding="latin1", on_bad_lines="skip"),
        dict(sep="\t", engine="python", dtype=str, encoding="latin1", on_bad_lines="skip"),
        dict(sep="|", engine="python", dtype=str, encoding="latin1", on_bad_lines="skip"),
    ]
    last_err = None
    for kwargs in attempts:
        try:
            df = pd.read_csv(path, **kwargs)
            if df.shape[1] >= 3:
                df.columns = sanitize_columns(df.columns)
                return df.fillna("")
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not parse {path}: {last_err}")

def norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

def pick_col(df: pd.DataFrame, *candidates):
    cmap = {norm_key(c): c for c in df.columns}
    for cand in candidates:
        key = norm_key(cand)
        if key in cmap:
            return cmap[key]
    return None

def get_series(df: pd.DataFrame, *candidates, default=""):
    col = pick_col(df, *candidates)
    if col:
        return df[col].astype(str).fillna("").str.strip()
    return pd.Series([default] * len(df), index=df.index)

def to_sql(df: pd.DataFrame, table_name: str):
    df.to_sql(table_name, engine(), schema="us", if_exists="replace", index=False, method="multi", chunksize=5000)

def main():
    run_sql_file(SQL_DIR / "01_us_recent_schema.sql")

    download(URLS["schools_2324"], RAW_2324 / "ccd_sch_029_2324_w_0a_050824.zip")
    download(URLS["schools_2324_docs"], RAW_2324 / "2023-24_Sch_Documentation_prelim.zip")
    download(URLS["lea_2324"], RAW_2324 / "ccd_lea_029_2324_w_0a_050824.zip")
    download(URLS["lea_2324_docs"], RAW_2324 / "2023-24_Lea_Documentation_prelim.zip")

    download(URLS["schools_2425"], RAW_2425 / "ccd_sch_029_2425_w_0a_051425.zip")
    download(URLS["schools_2425_docs"], RAW_2425 / "2024-25_Sch_Documentation_prelim.zip")
    download(URLS["lea_2425"], RAW_2425 / "ccd_lea_029_2425_w_0a_051425.zip")
    download(URLS["lea_2425_docs"], RAW_2425 / "2024-25_Lea_Documentation_prelim.zip")

    for z in RAW_2324.glob("*.zip"):
        extract_zip(z, EXT_2324 / z.stem)
    for z in RAW_2425.glob("*.zip"):
        extract_zip(z, EXT_2425 / z.stem)

    school_flat = choose_flat_file(EXT_2324 / "ccd_sch_029_2324_w_0a_050824")
    lea_flat = choose_flat_file(EXT_2324 / "ccd_lea_029_2324_w_0a_050824")

    if school_flat is None:
        raise RuntimeError("No 2023-24 school flat file found after extraction.")
    if lea_flat is None:
        raise RuntimeError("No 2023-24 LEA flat file found after extraction.")

    schools_raw = read_any(school_flat)
    lea_raw = read_any(lea_flat)

    to_sql(schools_raw, "stg_schools_2023_2024_raw")
    to_sql(lea_raw, "stg_lea_2023_2024_raw")

    school_id = get_series(schools_raw, "ncessch", "school_id", "nces_school_id")
    school_name = get_series(schools_raw, "sch_name", "school_name", "name")
    district_id = get_series(schools_raw, "leaid", "nceslea", "district_id", "lea_id")
    district_name = get_series(schools_raw, "lea_name", "district_name", "agency_name")
    state_abbr = get_series(schools_raw, "stabr", "state_abbr", "state_code", "st").str.upper()
    state_name = get_series(schools_raw, "state_name", "state", "stnam")
    state_name = state_name.where(state_name != "", state_abbr.map(STATE_ABBR_TO_NAME).fillna(state_abbr))
    city = get_series(schools_raw, "mcity", "city")
    county_name = get_series(schools_raw, "county_name", "county", "coname")
    zip_code = get_series(schools_raw, "mzip", "zip", "zip_code")
    locale = get_series(schools_raw, "ulocal", "locale", "locale_text")
    school_type = get_series(schools_raw, "type", "school_type")
    school_level = get_series(schools_raw, "level", "school_level")
    low_grade = get_series(schools_raw, "gslo", "low_grade")
    high_grade = get_series(schools_raw, "gshi", "high_grade")
    charter_status = get_series(schools_raw, "charter", "charter_status")
    operational_status = get_series(schools_raw, "status", "school_status", "operational_status")
    latitude = get_series(schools_raw, "latitude", "lat")
    longitude = get_series(schools_raw, "longitude", "lon", "lng")

    dim_schools = pd.DataFrame({
        "school_year": "2023-2024",
        "school_id": school_id,
        "school_name": school_name,
        "district_id": district_id,
        "district_name": district_name,
        "state_name": state_name,
        "state_abbr": state_abbr,
        "city": city,
        "county_name": county_name,
        "zip_code": zip_code,
        "locale": locale,
        "school_type": school_type,
        "school_level": school_level,
        "low_grade": low_grade,
        "high_grade": high_grade,
        "charter_status": charter_status,
        "operational_status": operational_status,
        "latitude": latitude,
        "longitude": longitude,
        "source_file": school_flat.name,
        "created_at": datetime.utcnow(),
    }).replace({"": None}).dropna(subset=["school_id"]).drop_duplicates(subset=["school_id"])

    lea_id = get_series(lea_raw, "leaid", "nceslea", "district_id", "lea_id")
    lea_name = get_series(lea_raw, "lea_name", "district_name", "agency_name")
    lea_state_abbr = get_series(lea_raw, "stabr", "state_abbr", "state_code", "st").str.upper()
    lea_state_name = get_series(lea_raw, "state_name", "state", "stnam")
    lea_state_name = lea_state_name.where(lea_state_name != "", lea_state_abbr.map(STATE_ABBR_TO_NAME).fillna(lea_state_abbr))
    lea_city = get_series(lea_raw, "mcity", "city")
    lea_zip = get_series(lea_raw, "mzip", "zip", "zip_code")
    lea_phone = get_series(lea_raw, "phone", "telephone", "phone_number")

    dim_districts = pd.DataFrame({
        "school_year": "2023-2024",
        "district_id": lea_id,
        "district_name": lea_name,
        "state_name": lea_state_name,
        "state_abbr": lea_state_abbr,
        "city": lea_city,
        "zip_code": lea_zip,
        "phone": lea_phone,
        "source_file": lea_flat.name,
        "created_at": datetime.utcnow(),
    }).replace({"": None}).dropna(subset=["district_id"]).drop_duplicates(subset=["district_id"])

    dim_states = (
        dim_schools.groupby(["school_year", "state_name", "state_abbr"], dropna=False)
        .agg(school_count=("school_id", "nunique"), district_count=("district_id", "nunique"))
        .reset_index()
    )
    dim_states["created_at"] = datetime.utcnow()

    to_sql(dim_states, "dim_states")
    to_sql(dim_districts, "dim_districts")
    to_sql(dim_schools, "dim_schools")

    empty_enrollment = pd.DataFrame(columns=[
        "school_year","state_name","state_abbr","district_id","district_name",
        "school_id","school_name","sex","race_ethnicity","grade_level",
        "student_count","source_file","created_at"
    ])
    empty_staff = pd.DataFrame(columns=[
        "school_year","state_name","state_abbr","district_id","district_name",
        "school_id","school_name","staff_category","teacher_fte","staff_fte",
        "source_file","created_at"
    ])
    empty_chars = pd.DataFrame(columns=[
        "school_year","state_name","state_abbr","district_id","district_name",
        "school_id","school_name","frpl_eligible","characteristic_name",
        "characteristic_value","source_file","created_at"
    ])
    empty_perf = pd.DataFrame(columns=[
        "school_year","state_name","state_abbr","subject","grade_level",
        "average_score","proficiency_pct","source_file","created_at"
    ])

    to_sql(empty_enrollment, "fact_enrollment")
    to_sql(empty_staff, "fact_staff")
    to_sql(empty_chars, "fact_school_characteristics")
    to_sql(empty_perf, "fact_performance_state")

    run_sql_file(SQL_DIR / "02_us_recent_views.sql")

    report = {
        "status": "success",
        "loaded_at_utc": datetime.utcnow().isoformat(),
        "primary_dashboard_year": "2023-2024",
        "optional_directory_year": "2024-2025",
        "school_flat_file": str(school_flat),
        "lea_flat_file": str(lea_flat),
        "stg_school_rows": int(len(schools_raw)),
        "stg_lea_rows": int(len(lea_raw)),
        "dim_states_rows": int(len(dim_states)),
        "dim_districts_rows": int(len(dim_districts)),
        "dim_schools_rows": int(len(dim_schools)),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"us_recent_load_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report written to: {out}")

if __name__ == "__main__":
    main()
PYEOF

echo "==> Writing validator script"
cat > "$REPO/scripts/us/validate_recent_us_schema.py" <<'PYEOF'
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine

REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "reports/us"

def load_db_config():
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", os.getenv("DB_DATABASE", "tutorcloud_db")),
        "user": os.getenv("DB_USER", "tutorcloud_admin"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    try:
        sys.path.insert(0, str(REPO))
        from utils.uae_page_renderer import DB_CONFIG as UAE_DB_CONFIG  # type: ignore
        if isinstance(UAE_DB_CONFIG, dict):
            for k in ("host", "port", "dbname", "user", "password"):
                if UAE_DB_CONFIG.get(k) not in (None, ""):
                    cfg[k] = UAE_DB_CONFIG[k]
    except Exception:
        pass
    return cfg

DB = load_db_config()

def engine():
    url = (
        f"postgresql+psycopg2://{quote_plus(str(DB['user']))}:{quote_plus(str(DB['password']))}"
        f"@{DB['host']}:{DB['port']}/{DB['dbname']}"
    )
    return create_engine(url, future=True)

def q(sql: str):
    return pd.read_sql(sql, engine())

def main():
    checks = {}
    tables = [
        "us.dim_states",
        "us.dim_districts",
        "us.dim_schools",
        "us.fact_enrollment",
        "us.fact_staff",
        "us.fact_school_characteristics",
        "us.fact_performance_state",
        "us.vw_dashboard_readiness",
    ]
    for t in tables:
        try:
            df = q(f"SELECT COUNT(*) AS c FROM {t}")
            checks[t] = int(df.iloc[0]["c"])
        except Exception as e:
            checks[t] = f"ERROR: {e}"

    result = {
        "validated_at_utc": datetime.utcnow().isoformat(),
        "checks": checks,
        "state_sample": q("SELECT * FROM us.dim_states ORDER BY school_count DESC, state_name LIMIT 10").to_dict("records"),
        "district_sample": q("SELECT * FROM us.dim_districts ORDER BY state_name, district_name LIMIT 10").to_dict("records"),
        "school_sample": q("SELECT * FROM us.dim_schools ORDER BY state_name, district_name, school_name LIMIT 10").to_dict("records"),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"us_recent_validate_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    print(f"Validation report written to: {out}")

if __name__ == "__main__":
    main()
PYEOF

echo "==> Writing placeholder US renderer and routing patch files"
cat > "$REPO/utils/us_page_renderer.py" <<'PYEOF'
"""
US dashboard renderer placeholder.
Data-first setup completed.
Next step is to build Home / State Dashboard / Analytics against us.* canonical tables.
"""

def render_us_home():
    raise NotImplementedError("US renderer scaffold not yet generated. Data layer is ready first.")

def render_us_state_dashboard():
    raise NotImplementedError("US renderer scaffold not yet generated. Data layer is ready first.")

def render_us_analytics():
    raise NotImplementedError("US renderer scaffold not yet generated. Data layer is ready first.")
PYEOF

cat > "$REPO/scripts/us/patch_us_routing.py" <<'PYEOF'
"""
Placeholder patch file.
Run routing patch only after full us_page_renderer.py is generated and validated.
"""
print("Routing patch placeholder created. Do not run until renderer scaffold is ready.")
PYEOF

echo "==> Installing Python dependencies"
"$PIP" install --quiet pandas sqlalchemy psycopg2-binary openpyxl xlsxwriter

echo "==> Syntax check"
"$PY" -m py_compile \
  "$REPO/scripts/us/load_recent_us_nces.py" \
  "$REPO/scripts/us/validate_recent_us_schema.py" \
  "$REPO/utils/us_page_renderer.py" \
  "$REPO/scripts/us/patch_us_routing.py"

echo "==> Running recent-year US NCES loader"
"$PY" "$REPO/scripts/us/load_recent_us_nces.py" | tee /tmp/us_recent_load.log

echo "==> Running validator"
"$PY" "$REPO/scripts/us/validate_recent_us_schema.py" | tee /tmp/us_recent_validate.log

echo "==> Latest US reports"
ls -1dt "$REPO"/reports/us/* | head -5

echo "==> Repo structure created successfully"
