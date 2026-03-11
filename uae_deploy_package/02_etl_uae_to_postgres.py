#!/usr/bin/env python3
"""
=============================================================
  02_etl_uae_to_postgres.py
  UAE Schools ETL Pipeline
  
  Reads CSVs/XLSX from etl/data/raw/uae/
  Normalises & loads into PostgreSQL tables:
    - uae_schools          (master school list)
    - uae_enrollment       (enrollment by school/year)
    - uae_staff            (teacher counts by zone)
    - uae_inspection       (KHDA/ADEK ratings)
  
  Run: python 02_etl_uae_to_postgres.py
=============================================================
"""
import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text
from pathlib import Path
import logging
from datetime import datetime

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"uae_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────
RAW_DIR = Path(os.environ.get("RAW_DIR", 
    os.path.expanduser("~/tutorcloud/etl/data/raw/uae")))

# Load DB config from .env (reuse existing settings.py pattern)
sys.path.insert(0, str(Path(__file__).parent.parent / 
    "tutorcloud-global-dashboard/src"))
try:
    from config.settings import Settings
    s = Settings()
    DB_URL = s.database_url  # postgresql://user:pass@host:5432/db
except Exception:
    # Fallback: read .env directly
    import dotenv
    dotenv.load_dotenv(os.path.expanduser(
        "~/tutorcloud/tutorcloud-global-dashboard/.env"))
    DB_URL = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'tutorcloud')}"
    )

engine = create_engine(DB_URL, pool_pre_ping=True)

# ──────────────────────────────────────────────────────────
# STEP 1: CREATE UAE TABLES
# ──────────────────────────────────────────────────────────
CREATE_TABLES_SQL = """
-- Master school registry (one row per school)
CREATE TABLE IF NOT EXISTS uae_schools (
    school_id           SERIAL PRIMARY KEY,
    source_id           VARCHAR(100),           -- original ID from KHDA/MOE
    source              VARCHAR(50),            -- 'KHDA_DUBAI' | 'MOE' | 'BAYANAT' | 'ADEK'
    name_en             VARCHAR(500) NOT NULL,
    name_ar             VARCHAR(500),
    emirate             VARCHAR(100),           -- Dubai/Abu Dhabi/Sharjah/Ajman/Fujairah/RAK/UAQ
    zone                VARCHAR(200),           -- education zone / area
    school_type         VARCHAR(50),            -- 'Government' | 'Private'
    gender              VARCHAR(50),            -- 'Mixed' | 'Male' | 'Female' | 'Boys' | 'Girls'
    curriculum          VARCHAR(200),           -- UK/American/IB/Indian/MOE/French etc
    grade_range         VARCHAR(100),           -- KG1-G12 / KG1-G6 etc
    established_year    SMALLINT,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    address             TEXT,
    telephone           VARCHAR(100),
    email               VARCHAR(200),
    website             VARCHAR(300),
    po_box              VARCHAR(50),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Annual enrollment per school
CREATE TABLE IF NOT EXISTS uae_enrollment (
    id                  SERIAL PRIMARY KEY,
    school_id           INTEGER REFERENCES uae_schools(school_id),
    academic_year       VARCHAR(20),            -- '2024-2025'
    total_students      INTEGER,
    male_students       INTEGER,
    female_students     INTEGER,
    uae_national        INTEGER,
    expat_students      INTEGER,
    education_level     VARCHAR(100),           -- KG/Primary/Middle/Secondary
    source              VARCHAR(50),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Inspection / performance ratings
CREATE TABLE IF NOT EXISTS uae_inspection (
    id                  SERIAL PRIMARY KEY,
    school_id           INTEGER REFERENCES uae_schools(school_id),
    inspection_year     VARCHAR(20),            -- '2023-2024'
    overall_rating      VARCHAR(50),            -- Outstanding/Very Good/Good/Acceptable/Weak
    rating_score        SMALLINT,               -- 5=Outstanding 4=Very Good 3=Good 2=Acceptable 1=Weak
    inspecting_body     VARCHAR(50),            -- 'KHDA' | 'ADEK' | 'MOE'
    report_url          TEXT,
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Staff / teachers per zone (from Bayanat)
CREATE TABLE IF NOT EXISTS uae_staff (
    id                  SERIAL PRIMARY KEY,
    academic_year       VARCHAR(20),
    emirate             VARCHAR(100),
    zone                VARCHAR(200),
    school_type         VARCHAR(50),
    school_stage        VARCHAR(100),
    total_staff         INTEGER,
    teaching_staff      INTEGER,
    non_teaching_staff  INTEGER,
    source              VARCHAR(50),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Summary / KPI table (pre-aggregated for fast dashboard queries)
CREATE TABLE IF NOT EXISTS uae_summary_by_emirate (
    id                  SERIAL PRIMARY KEY,
    academic_year       VARCHAR(20),
    emirate             VARCHAR(100),
    total_schools       INTEGER,
    govt_schools        INTEGER,
    private_schools     INTEGER,
    total_students      INTEGER,
    total_staff         INTEGER,
    outstanding_pct     NUMERIC(5,2),
    very_good_pct       NUMERIC(5,2),
    good_pct            NUMERIC(5,2),
    acceptable_pct      NUMERIC(5,2),
    weak_pct            NUMERIC(5,2),
    most_common_curriculum VARCHAR(200),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast dashboard queries
CREATE INDEX IF NOT EXISTS idx_uae_schools_emirate 
    ON uae_schools(emirate);
CREATE INDEX IF NOT EXISTS idx_uae_schools_type 
    ON uae_schools(school_type);
CREATE INDEX IF NOT EXISTS idx_uae_schools_curriculum 
    ON uae_schools(curriculum);
CREATE INDEX IF NOT EXISTS idx_uae_enrollment_year 
    ON uae_enrollment(academic_year);
CREATE INDEX IF NOT EXISTS idx_uae_inspection_year 
    ON uae_inspection(inspection_year);
CREATE INDEX IF NOT EXISTS idx_uae_inspection_rating 
    ON uae_inspection(overall_rating);
"""

# ──────────────────────────────────────────────────────────
# STEP 2: NORMALISATION HELPERS
# ──────────────────────────────────────────────────────────
RATING_MAP = {
    "outstanding": 5, "very good": 4, "good": 3,
    "acceptable": 2, "weak": 1, "inadequate": 1
}

EMIRATE_MAP = {
    # normalise common variants
    "dubai": "Dubai",
    "abu dhabi": "Abu Dhabi",
    "sharjah": "Sharjah",
    "ajman": "Ajman",
    "fujairah": "Fujairah",
    "rak": "Ras Al Khaimah",
    "ras al khaimah": "Ras Al Khaimah",
    "umm al quwain": "Umm Al Quwain",
    "uaq": "Umm Al Quwain",
    "al ain": "Abu Dhabi",   # Al Ain is in Abu Dhabi emirate
}

def norm_emirate(val: str) -> str:
    if not val:
        return "Unknown"
    return EMIRATE_MAP.get(str(val).strip().lower(), str(val).strip().title())

def norm_rating(val: str) -> tuple:
    """Returns (rating_text, rating_score)"""
    if not val:
        return (None, None)
    clean = str(val).strip().lower()
    for k, v in RATING_MAP.items():
        if k in clean:
            return (str(val).strip().title(), v)
    return (str(val).strip().title(), None)

def norm_year(val) -> int | None:
    try:
        y = int(str(val)[:4])
        return y if 1950 <= y <= 2030 else None
    except Exception:
        return None

# ──────────────────────────────────────────────────────────
# STEP 3: LOAD KHDA DUBAI PULSE CSV
# ──────────────────────────────────────────────────────────
def load_khda_csv(path: Path) -> pd.DataFrame:
    """
    Columns expected from Dubai Pulse school_search.csv:
    education_center_id, name_eng, name_ar, lat, long,
    established_on, overall_performance_en, inspection_year,
    curriculum_en, area_en, student_count, telephone,
    web_address, email, inspection_report_pdf_link_en
    """
    log.info(f"Reading KHDA CSV: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    log.info(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
    
    # Rename to standard schema
    col_map = {
        "education_center_id": "source_id",
        "name_eng": "name_en",
        "name_ar": "name_ar",
        "lat": "latitude",
        "long": "longitude",
        "curriculum_en": "curriculum",
        "area_en": "zone",
        "student_count": "total_students",
        "telephone": "telephone",
        "web_address": "website",
        "email": "email",
        "overall_performance_en": "overall_rating",
        "inspection_year": "inspection_year",
        "inspection_report_pdf_link_en": "report_url",
        "established_on": "established_on",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    df["emirate"] = "Dubai"
    df["school_type"] = "Private"
    df["source"] = "KHDA_DUBAI"
    df["established_year"] = df.get("established_on", pd.Series()).apply(norm_year)
    rating_parsed = df.get("overall_rating", pd.Series()).apply(norm_rating)
    df["overall_rating"] = rating_parsed.apply(lambda x: x[0])
    df["rating_score"] = rating_parsed.apply(lambda x: x[1])
    
    return df

# ──────────────────────────────────────────────────────────
# STEP 4: LOAD KHDA XLSX (richer dataset)
# ──────────────────────────────────────────────────────────
def load_khda_xlsx(path: Path) -> pd.DataFrame:
    log.info(f"Reading KHDA XLSX: {path}")
    try:
        xl = pd.ExcelFile(path)
        log.info(f"  Sheets: {xl.sheet_names}")
        # Try first sheet that looks like school data
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            if len(df) > 10:
                log.info(f"  Using sheet: {sheet} ({len(df)} rows)")
                break
    except Exception as e:
        log.warning(f"  XLSX read failed: {e}")
        return pd.DataFrame()
    
    df["source"] = "KHDA_XLSX"
    df["emirate"] = "Dubai"
    return df

# ──────────────────────────────────────────────────────────
# STEP 5: LOAD BAYANAT GE PUBLIC/PRIVATE SCHOOLS CSV
# ──────────────────────────────────────────────────────────
def load_bayanat_schools(path: Path, school_type: str = "Government") -> pd.DataFrame:
    """
    Expected columns from Bayanat GE Public Schools 2018-2024:
    Academic Year, Emirate, Zone, School Type, School Stage,
    Number of Schools, Male Schools, Female Schools, Mixed Schools
    """
    log.info(f"Reading Bayanat CSV: {path}")
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        df = pd.read_excel(path)
    log.info(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
    
    # Normalise column names (Bayanat sometimes uses Arabic-English mix)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df["school_type"] = school_type
    df["source"] = "BAYANAT"
    
    if "emirate" in df.columns:
        df["emirate"] = df["emirate"].apply(norm_emirate)
    
    return df

# ──────────────────────────────────────────────────────────
# STEP 6: LOAD MOE XLSX (Schools by Emirate/Curriculum)
# ──────────────────────────────────────────────────────────
def load_moe_schools(path: Path) -> pd.DataFrame:
    log.info(f"Reading MOE XLSX: {path}")
    try:
        xl = pd.ExcelFile(path)
        log.info(f"  Sheets: {xl.sheet_names}")
        df = xl.parse(xl.sheet_names[0])
    except Exception as e:
        log.warning(f"  MOE file read failed: {e}")
        return pd.DataFrame()
    
    df.columns = [str(c).strip() for c in df.columns]
    df["source"] = "MOE"
    if "Emirate" in df.columns:
        df["emirate"] = df["Emirate"].apply(norm_emirate)
    
    return df

# ──────────────────────────────────────────────────────────
# STEP 7: WRITE TO POSTGRES
# ──────────────────────────────────────────────────────────
def upsert_schools(df: pd.DataFrame, conn):
    """Insert into uae_schools; skip duplicates by source+source_id."""
    SCHOOL_COLS = [
        "source_id", "source", "name_en", "name_ar", "emirate", "zone",
        "school_type", "gender", "curriculum", "grade_range",
        "established_year", "latitude", "longitude",
        "address", "telephone", "email", "website", "po_box"
    ]
    # Only keep columns that exist in df
    cols = [c for c in SCHOOL_COLS if c in df.columns]
    insert_df = df[cols].copy()
    insert_df = insert_df.where(pd.notnull(insert_df), None)
    
    records = [tuple(r) for r in insert_df.itertuples(index=False)]
    if not records:
        return 0
    
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    sql = f"""
        INSERT INTO uae_schools ({col_list})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """
    cur = conn.cursor()
    cur.executemany(sql, records)
    conn.commit()
    log.info(f"  Upserted {len(records)} school records")
    return len(records)

def insert_inspection(df: pd.DataFrame, school_id_map: dict, conn):
    """Insert inspection ratings linked to school_id."""
    if "overall_rating" not in df.columns:
        return
    
    records = []
    for _, row in df.iterrows():
        sid = school_id_map.get(str(row.get("source_id", "")))
        if not sid:
            continue
        rating_text, rating_score = norm_rating(row.get("overall_rating", ""))
        records.append((
            sid,
            str(row.get("inspection_year", "2024-2025")),
            rating_text,
            rating_score,
            "KHDA" if row.get("source", "").startswith("KHDA") else "MOE",
            row.get("report_url"),
        ))
    
    if records:
        sql = """
            INSERT INTO uae_inspection 
                (school_id, inspection_year, overall_rating, rating_score, 
                 inspecting_body, report_url)
            VALUES %s ON CONFLICT DO NOTHING
        """
        cur = conn.cursor()
        execute_values(cur, sql, records)
        conn.commit()
        log.info(f"  Inserted {len(records)} inspection records")

def refresh_summary(conn):
    """Rebuild uae_summary_by_emirate from live tables."""
    sql = """
    TRUNCATE uae_summary_by_emirate;
    INSERT INTO uae_summary_by_emirate 
        (academic_year, emirate, total_schools, govt_schools, private_schools,
         total_students, outstanding_pct, very_good_pct, good_pct, 
         acceptable_pct, weak_pct, most_common_curriculum)
    SELECT
        COALESCE(e.academic_year, '2024-2025') AS academic_year,
        s.emirate,
        COUNT(DISTINCT s.school_id)              AS total_schools,
        COUNT(DISTINCT s.school_id) FILTER (WHERE s.school_type = 'Government') AS govt_schools,
        COUNT(DISTINCT s.school_id) FILTER (WHERE s.school_type = 'Private')    AS private_schools,
        COALESCE(SUM(e.total_students), 0)       AS total_students,
        ROUND(100.0 * COUNT(*) FILTER (WHERE i.overall_rating = 'Outstanding') 
              / NULLIF(COUNT(i.*),0), 2)          AS outstanding_pct,
        ROUND(100.0 * COUNT(*) FILTER (WHERE i.overall_rating = 'Very Good')
              / NULLIF(COUNT(i.*),0), 2)          AS very_good_pct,
        ROUND(100.0 * COUNT(*) FILTER (WHERE i.overall_rating = 'Good')
              / NULLIF(COUNT(i.*),0), 2)          AS good_pct,
        ROUND(100.0 * COUNT(*) FILTER (WHERE i.overall_rating = 'Acceptable')
              / NULLIF(COUNT(i.*),0), 2)          AS acceptable_pct,
        ROUND(100.0 * COUNT(*) FILTER (WHERE i.overall_rating = 'Weak')
              / NULLIF(COUNT(i.*),0), 2)          AS weak_pct,
        MODE() WITHIN GROUP (ORDER BY s.curriculum) AS most_common_curriculum
    FROM uae_schools s
    LEFT JOIN uae_enrollment e  ON s.school_id = e.school_id
    LEFT JOIN uae_inspection i  ON s.school_id = i.school_id
    WHERE s.is_active = TRUE
    GROUP BY s.emirate, e.academic_year;
    """
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    log.info("  Summary table refreshed")

# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────
def main():
    log.info("=== UAE ETL Pipeline Starting ===")
    
    with engine.raw_connection() as conn:
        # 1. Create tables
        log.info("Step 1: Creating UAE tables...")
        cur = conn.cursor()
        cur.execute(CREATE_TABLES_SQL)
        conn.commit()
        log.info("  Tables created/verified")
        
        # 2. Load KHDA Dubai Pulse CSV (if present)
        khda_csv = RAW_DIR / "khda_dubai_private_schools.csv"
        if khda_csv.exists():
            df_khda = load_khda_csv(khda_csv)
            upsert_schools(df_khda, conn)
            
            # Get school_id mapping for inspection load
            cur.execute("SELECT source_id, school_id FROM uae_schools WHERE source='KHDA_DUBAI'")
            school_id_map = {r[0]: r[1] for r in cur.fetchall()}
            insert_inspection(df_khda, school_id_map, conn)
        else:
            log.warning(f"  {khda_csv} not found – skipping KHDA CSV")
        
        # 3. Load KHDA XLSX (if present)
        khda_xlsx = RAW_DIR / "khda_dubai_schools_full.xlsx"
        if khda_xlsx.exists():
            df_xlsx = load_khda_xlsx(khda_xlsx)
            if not df_xlsx.empty:
                upsert_schools(df_xlsx, conn)
        else:
            log.warning(f"  {khda_xlsx} not found – skipping KHDA XLSX")
        
        # 4. Load Bayanat GE Public Schools (if present)
        bayanat_pub = RAW_DIR / "ge_public_schools_2018_2024.csv"
        if bayanat_pub.exists():
            df_pub = load_bayanat_schools(bayanat_pub, "Government")
            log.info(f"  Bayanat public schools loaded: {len(df_pub)} rows")
            # Aggregate and insert to uae_staff table
        else:
            log.warning(f"  {bayanat_pub} not found – skipping Bayanat public schools")
        
        # 5. Load MOE Schools by Emirate (if present)
        moe_file = RAW_DIR / "moe_schools_by_emirate.xlsx"
        if moe_file.exists():
            df_moe = load_moe_schools(moe_file)
            if not df_moe.empty:
                upsert_schools(df_moe, conn)
        else:
            log.warning(f"  {moe_file} not found – skipping MOE data")
        
        # 6. Refresh summary table
        log.info("Step 6: Refreshing summary table...")
        try:
            refresh_summary(conn)
        except Exception as e:
            log.warning(f"  Summary refresh error (non-fatal): {e}")
        
        # 7. Row counts
        cur.execute("SELECT COUNT(*) FROM uae_schools")
        log.info(f"  uae_schools total rows: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM uae_inspection")
        log.info(f"  uae_inspection total rows: {cur.fetchone()[0]}")
    
    log.info("=== UAE ETL Pipeline Complete ===")

if __name__ == "__main__":
    main()
