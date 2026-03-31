#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2

ROOT = Path("/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard")
RAW_ZIP = ROOT / "data" / "us_pss" / "raw" / "pss2122_pu_csv.zip"
EXTRACT_DIR = ROOT / "data" / "us_pss" / "extracted"
NORM_CSV = EXTRACT_DIR / "pss_private_normalized_2021_2022.csv"
REPORT_PATH = ROOT / "reports" / "us" / "us_pss_gap_audit_report.json"

SCHEMA = "us"
STAGE_TABLE = "stg_pss_private_school_2021_2022"
PRIVATE_DIM_TABLE = "dim_private_schools_pss_2021_2022"
DASHBOARD_YEAR = "2024-2025"
OFFICIAL_PRIVATE_SCHOOLS_2021_22 = 29730  # NCES Fast Facts / PSS

def log(msg: str) -> None:
    print(msg, flush=True)

def sanitize(col: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(col).strip().lower()).strip("_")

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

def pick(headers: list[str], candidates: list[str]) -> str | None:
    hs = set(headers)
    for c in candidates:
        if c in hs:
            return c
    return None

def read_zip_csv(zip_path: Path, member: str):
    raw_bytes = None
    with zipfile.ZipFile(zip_path, "r") as zf:
        raw_bytes = zf.read(member)

    last_err = None
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw_bytes.decode(enc)
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            headers = reader.fieldnames or []
            return headers, rows, enc
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not decode/read ZIP member {member}: {last_err}")

def read_csv_file(path: Path):
    last_err = None
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(path, "r", newline="", encoding=enc) as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
                headers = reader.fieldnames or []
                return headers, rows, enc
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not read CSV {path}: {last_err}")

def q_scalar(cur, sql: str, params=None):
    cur.execute(sql, params or [])
    row = cur.fetchone()
    return row[0] if row else None

def table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
        """,
        [schema, table],
    )
    return bool(cur.fetchone()[0])

def file_row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    _, rows, _ = read_csv_file(path)
    return len(rows)

def main():
    if not RAW_ZIP.exists():
        raise SystemExit(f"Missing ZIP: {RAW_ZIP}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(RAW_ZIP, "r") as zf:
        members = zf.namelist()
        csv_members = [m for m in members if m.lower().endswith(".csv")]

    if not csv_members:
        raise SystemExit("No CSV members found inside PSS ZIP.")

    selected_member = csv_members[0]
    raw_headers, raw_rows, raw_encoding = read_zip_csv(RAW_ZIP, selected_member)
    san_headers = [sanitize(h) for h in raw_headers]

    id_col = pick(san_headers, ["ppin", "school_id", "schoolid", "id"])
    name_col = pick(san_headers, ["pinst", "school_name", "school", "name"])
    city_col = pick(san_headers, ["pcity", "city"])
    state_col = pick(san_headers, ["pstabb", "state_abbr", "st", "state"])
    zip_col = pick(san_headers, ["pzip", "zip", "zip_code"])
    phone_col = pick(san_headers, ["pphone", "phone"])
    level_col = pick(san_headers, ["level", "school_level"])
    type_col = pick(san_headers, ["typology", "school_type", "private_school_type", "relig", "orientation"])
    students_col = pick(san_headers, ["numstuds", "enrollment", "student_count", "num_students"])
    teachers_col = pick(san_headers, ["numteach", "numteachers", "teacher_count", "teachers", "num_teachers"])

    mapped = {
        "id_col": id_col,
        "name_col": name_col,
        "city_col": city_col,
        "state_col": state_col,
        "zip_col": zip_col,
        "phone_col": phone_col,
        "level_col": level_col,
        "type_col": type_col,
        "students_col": students_col,
        "teachers_col": teachers_col,
    }

    sanitized_rows = []
    for row in raw_rows:
        sanitized_rows.append({sanitize(k): (v if v is not None else "") for k, v in row.items()})

    raw_total = len(sanitized_rows)
    blank_name = 0
    blank_state = 0
    blank_both = 0
    raw_state_counts = Counter()
    norm_state_counts = Counter()
    drop_reasons = Counter()
    duplicate_id_counter = Counter()

    if id_col:
        for row in sanitized_rows:
            rid = str(row.get(id_col, "")).strip()
            if rid:
                duplicate_id_counter[rid] += 1

    duplicate_ids = sum(1 for _, c in duplicate_id_counter.items() if c > 1)
    duplicate_rows_above_first = sum((c - 1) for _, c in duplicate_id_counter.items() if c > 1)

    normalized_survivors = 0

    for row in sanitized_rows:
        school_name = str(row.get(name_col, "")).strip() if name_col else ""
        state_abbr = str(row.get(state_col, "")).strip().upper() if state_col else ""

        if state_abbr:
            raw_state_counts[state_abbr] += 1

        if not school_name:
            blank_name += 1
            drop_reasons["blank_school_name"] += 1
            if not state_abbr:
                blank_both += 1
            continue

        if not state_abbr:
            blank_state += 1
            # current normalization keeps these rows, but tags them Unknown/blank state
            drop_reasons["blank_state_but_kept"] += 1

        normalized_survivors += 1
        norm_state_counts[state_abbr or "<<BLANK_STATE>>"] += 1

    normalized_file_rows = file_row_count(NORM_CSV)

    conn = psycopg2.connect(**load_db_params())
    try:
        cur = conn.cursor()

        stage_rows = q_scalar(cur, f"SELECT COUNT(*) FROM {SCHEMA}.{STAGE_TABLE}") if table_exists(cur, SCHEMA, STAGE_TABLE) else None
        private_dim_rows = q_scalar(cur, f"SELECT COUNT(*) FROM {SCHEMA}.{PRIVATE_DIM_TABLE}") if table_exists(cur, SCHEMA, PRIVATE_DIM_TABLE) else None

        pss_dim_rows = q_scalar(
            cur,
            f"""
            SELECT COUNT(*)
            FROM {SCHEMA}.dim_schools
            WHERE school_year = %s
              AND COALESCE(source_system, '') = 'PSS'
            """,
            [DASHBOARD_YEAR],
        ) if table_exists(cur, SCHEMA, "dim_schools") else None

        pss_fact_rows = q_scalar(
            cur,
            f"""
            SELECT COUNT(*)
            FROM {SCHEMA}.fact_school_totals f
            JOIN {SCHEMA}.dim_schools ds
              ON ds.school_year = f.school_year
             AND ds.school_id = f.school_id
            WHERE ds.school_year = %s
              AND COALESCE(ds.source_system, '') = 'PSS'
            """,
            [DASHBOARD_YEAR],
        ) if table_exists(cur, SCHEMA, "fact_school_totals") and table_exists(cur, SCHEMA, "dim_schools") else None

        management_distribution = []
        if table_exists(cur, SCHEMA, "dim_schools"):
            cur.execute(
                f"""
                SELECT COALESCE(management_type, '<<NULL>>') AS management_type,
                       COALESCE(source_system, '<<NULL>>') AS source_system,
                       COUNT(*) AS rows
                FROM {SCHEMA}.dim_schools
                WHERE school_year = %s
                GROUP BY 1,2
                ORDER BY 1,2
                """,
                [DASHBOARD_YEAR],
            )
            management_distribution = cur.fetchall()

    finally:
        conn.close()

    top_state_deltas = []
    all_states = sorted(set(raw_state_counts.keys()) | set(norm_state_counts.keys()))
    for st in all_states:
        raw_c = raw_state_counts.get(st, 0)
        norm_c = norm_state_counts.get(st, 0)
        delta = raw_c - norm_c
        if delta != 0:
            top_state_deltas.append({"state": st, "raw_rows": raw_c, "normalized_rows": norm_c, "dropped_rows": delta})
    top_state_deltas = sorted(top_state_deltas, key=lambda x: (-x["dropped_rows"], x["state"]))[:25]

    report = {
        "official_private_school_benchmark_2021_22": OFFICIAL_PRIVATE_SCHOOLS_2021_22,
        "zip_path": str(RAW_ZIP),
        "zip_csv_members": csv_members,
        "selected_csv_member": selected_member,
        "raw_csv_encoding": raw_encoding,
        "raw_csv_headers_sample": raw_headers[:50],
        "sanitized_headers_sample": san_headers[:50],
        "column_mapping": mapped,
        "raw_total_rows_in_selected_csv": raw_total,
        "normalized_survivors_by_current_logic": normalized_survivors,
        "normalized_csv_file_rows": normalized_file_rows,
        "rows_lost_raw_to_current_normalization": raw_total - normalized_survivors,
        "rows_missing_vs_official_benchmark": OFFICIAL_PRIVATE_SCHOOLS_2021_22 - normalized_survivors,
        "blank_school_name_rows": blank_name,
        "blank_state_rows_kept": blank_state,
        "blank_name_and_blank_state_rows": blank_both,
        "duplicate_nonblank_id_values": duplicate_ids,
        "duplicate_rows_above_first_for_id": duplicate_rows_above_first,
        "drop_reasons": dict(drop_reasons),
        "top_state_deltas_raw_vs_normalized": top_state_deltas,
        "db_counts": {
            "stage_rows": stage_rows,
            "private_dim_rows": private_dim_rows,
            "pss_rows_in_dim_schools": pss_dim_rows,
            "pss_rows_in_fact_school_totals": pss_fact_rows,
        },
        "management_distribution": management_distribution,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n===== PSS GAP AUDIT SUMMARY =====")
    print(json.dumps({
        "official_private_school_benchmark_2021_22": OFFICIAL_PRIVATE_SCHOOLS_2021_22,
        "selected_csv_member": selected_member,
        "raw_total_rows_in_selected_csv": raw_total,
        "normalized_survivors_by_current_logic": normalized_survivors,
        "normalized_csv_file_rows": normalized_file_rows,
        "rows_lost_raw_to_current_normalization": raw_total - normalized_survivors,
        "rows_missing_vs_official_benchmark": OFFICIAL_PRIVATE_SCHOOLS_2021_22 - normalized_survivors,
        "blank_school_name_rows": blank_name,
        "blank_state_rows_kept": blank_state,
        "duplicate_nonblank_id_values": duplicate_ids,
        "duplicate_rows_above_first_for_id": duplicate_rows_above_first,
    }, indent=2))

    print("\n===== COLUMN MAPPING =====")
    print(json.dumps(mapped, indent=2))

    print("\n===== ZIP CSV MEMBERS =====")
    print(json.dumps(csv_members, indent=2))

    print("\n===== DB COUNTS =====")
    print(json.dumps(report["db_counts"], indent=2))

    print("\n===== MANAGEMENT DISTRIBUTION =====")
    print(json.dumps(management_distribution, indent=2))

    print("\n===== TOP STATE DELTAS (RAW vs NORMALIZED) =====")
    print(json.dumps(top_state_deltas, indent=2))

    print(f"\nReport written to: {REPORT_PATH}")

if __name__ == "__main__":
    main()
