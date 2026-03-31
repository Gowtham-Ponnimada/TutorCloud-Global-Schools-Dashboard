#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import math
import re
import zipfile
from pathlib import Path

ROOT = Path("/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard")
RAW_ZIP = ROOT / "data" / "us_pss" / "raw" / "pss2122_pu_csv.zip"
REPORT_PATH = ROOT / "reports" / "us" / "us_pss_weight_audit_report.json"

OFFICIAL_PRIVATE_SCHOOLS = 29727
OFFICIAL_PRIVATE_STUDENTS = 4731303
OFFICIAL_PRIVATE_FTE_TEACHERS = 482571

def sanitize(col: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(col).strip().lower()).strip("_")

def to_float(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s == "" or s in {"NA", "N/A", ".", "..", "NULL", "None"}:
        return None
    try:
        return float(s)
    except Exception:
        return None

def pct_diff(a, b):
    if a is None or b in (None, 0):
        return None
    return round(((a - b) / b) * 100.0, 4)

if not RAW_ZIP.exists():
    raise SystemExit(f"Missing ZIP: {RAW_ZIP}")

with zipfile.ZipFile(RAW_ZIP, "r") as zf:
    csv_members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
    if not csv_members:
        raise SystemExit("No CSV member found in ZIP.")
    member = csv_members[0]
    raw_bytes = zf.read(member)

rows = None
fieldnames = None
used_encoding = None
last_err = None
for enc in ("utf-8-sig", "latin-1", "cp1252"):
    try:
        text = raw_bytes.decode(enc)
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        fieldnames = reader.fieldnames or []
        used_encoding = enc
        break
    except Exception as e:
        last_err = e

if rows is None:
    raise SystemExit(f"Unable to read CSV: {last_err}")

san_fields = [sanitize(f) for f in fieldnames]
field_map = dict(zip(san_fields, fieldnames))

# Strong candidate weight fields commonly seen in NCES public-use files
weight_candidates_priority = [
    "pfnlwt",
    "finalwt",
    "final_weight",
    "weight",
    "wt",
    "schwt",
    "schoolwt",
    "wgt",
]

student_candidates_priority = [
    "numstuds",
    "enrollment",
    "student_count",
    "num_students",
]

teacher_candidates_priority = [
    "numteach",
    "numteachers",
    "teacher_count",
    "teachers",
    "num_teachers",
    "fteteach",
    "fte_teachers",
]

available_weight_candidates = [c for c in san_fields if c in weight_candidates_priority]
available_weight_candidates += [c for c in san_fields if ("wt" in c or "weight" in c) and c not in available_weight_candidates]

available_student_candidates = [c for c in student_candidates_priority if c in san_fields]
available_teacher_candidates = [c for c in teacher_candidates_priority if c in san_fields]

raw_row_count = len(rows)

results = []
for wcol in available_weight_candidates:
    worig = field_map[wcol]
    scol = available_student_candidates[0] if available_student_candidates else None
    tcol = available_teacher_candidates[0] if available_teacher_candidates else None

    sum_w = 0.0
    nonnull_w = 0
    bad_w = 0

    weighted_students = 0.0
    weighted_students_nonnull = 0

    weighted_teachers = 0.0
    weighted_teachers_nonnull = 0

    for row in rows:
        w = to_float(row.get(worig))
        if w is None:
            bad_w += 1
            continue
        nonnull_w += 1
        sum_w += w

        if scol:
            s = to_float(row.get(field_map[scol]))
            if s is not None:
                weighted_students += w * s
                weighted_students_nonnull += 1

        if tcol:
            t = to_float(row.get(field_map[tcol]))
            if t is not None:
                weighted_teachers += w * t
                weighted_teachers_nonnull += 1

    results.append({
        "weight_field_sanitized": wcol,
        "weight_field_original": worig,
        "non_null_weight_rows": nonnull_w,
        "null_or_bad_weight_rows": bad_w,
        "weighted_school_estimate_sum_weights": round(sum_w, 3),
        "school_estimate_diff_from_official": round(sum_w - OFFICIAL_PRIVATE_SCHOOLS, 3),
        "school_estimate_pct_diff_from_official": pct_diff(sum_w, OFFICIAL_PRIVATE_SCHOOLS),
        "student_base_field_used": scol,
        "teacher_base_field_used": tcol,
        "weighted_students_estimate": round(weighted_students, 3) if weighted_students_nonnull else None,
        "students_estimate_diff_from_official": round(weighted_students - OFFICIAL_PRIVATE_STUDENTS, 3) if weighted_students_nonnull else None,
        "students_estimate_pct_diff_from_official": pct_diff(weighted_students, OFFICIAL_PRIVATE_STUDENTS) if weighted_students_nonnull else None,
        "weighted_teachers_estimate": round(weighted_teachers, 3) if weighted_teachers_nonnull else None,
        "teachers_estimate_diff_from_official": round(weighted_teachers - OFFICIAL_PRIVATE_FTE_TEACHERS, 3) if weighted_teachers_nonnull else None,
        "teachers_estimate_pct_diff_from_official": pct_diff(weighted_teachers, OFFICIAL_PRIVATE_FTE_TEACHERS) if weighted_teachers_nonnull else None,
    })

# Sort by closeness to official school estimate
results_sorted = sorted(
    results,
    key=lambda r: abs(r["school_estimate_diff_from_official"]) if r["school_estimate_diff_from_official"] is not None else math.inf
)

report = {
    "zip_path": str(RAW_ZIP),
    "selected_csv_member": member,
    "encoding_used": used_encoding,
    "raw_row_count": raw_row_count,
    "official_targets": {
        "private_schools": OFFICIAL_PRIVATE_SCHOOLS,
        "private_students": OFFICIAL_PRIVATE_STUDENTS,
        "private_fte_teachers": OFFICIAL_PRIVATE_FTE_TEACHERS,
    },
    "available_weight_candidates": available_weight_candidates,
    "available_student_candidates": available_student_candidates,
    "available_teacher_candidates": available_teacher_candidates,
    "top_weight_results": results_sorted[:10],
    "all_results_count": len(results_sorted),
}

REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("\n===== PSS WEIGHT AUDIT SUMMARY =====")
print(json.dumps({
    "selected_csv_member": member,
    "raw_row_count": raw_row_count,
    "available_weight_candidates": available_weight_candidates,
    "available_student_candidates": available_student_candidates,
    "available_teacher_candidates": available_teacher_candidates,
}, indent=2))

print("\n===== TOP WEIGHT RESULTS =====")
print(json.dumps(results_sorted[:10], indent=2))

print(f"\nReport written to: {REPORT_PATH}")
