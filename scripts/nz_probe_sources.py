from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd

ROOT = Path("data/nz")
RAW = ROOT / "raw"
PROF = ROOT / "profiling"
PROC = ROOT / "processed"

RAW.mkdir(parents=True, exist_ok=True)
PROF.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

SCHOOLS_RESOURCE_ID = "4b292323-9fcc-41f8-814b-3c7b19cf14b3"

SOURCES = {
    "schools_directory_api": {
        "type": "ckan_datastore",
        "resource_id": SCHOOLS_RESOURCE_ID,
        "url": "https://catalogue.data.govt.nz/api/3/action/datastore_search",
        "target_csv": RAW / "nz_schools_directory_api.csv",
        "target_meta": PROF / "nz_schools_directory_api_meta.json",
    },
    "school_rolls_by_school": {
        "type": "xlsx",
        "url": "https://www.educationcounts.govt.nz/statistics/school-rolls/downloads/2-Student-rolls-by-school-2010-2025-v2.xlsx",
        "target": RAW / "nz_school_rolls_by_school.xlsx",
    },
    "teacher_numbers_by_school": {
        "type": "xlsx",
        "url": "https://www.educationcounts.govt.nz/__data/assets/excel_doc/0006/215727/Teacher-numbers-by-school.xlsx",
        "target": RAW / "nz_teacher_numbers_by_school.xlsx",
    },
    "number_of_schools_timeseries": {
        "type": "xlsx",
        "url": "https://www.educationcounts.govt.nz/__data/assets/excel_doc/0014/152330/1-Time-series-Number-of-schools-1996-2025.xlsx",
        "target": RAW / "nz_number_of_schools_timeseries.xlsx",
    },
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) TutorCloud-NZ-Builder/1.0",
    "Accept": "*/*",
})

run_report = {
    "run_utc": datetime.utcnow().isoformat() + "Z",
    "downloads": {},
    "profiles": {},
}

def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))

def download_ckan_datastore():
    cfg = SOURCES["schools_directory_api"]
    rows = []
    offset = 0
    limit = 5000
    total = None

    while True:
        r = session.get(
            cfg["url"],
            params={
                "resource_id": cfg["resource_id"],
                "limit": limit,
                "offset": offset,
            },
            timeout=60,
        )
        r.raise_for_status()
        payload = r.json()
        if not payload.get("success"):
            raise RuntimeError(f"CKAN API unsuccessful response: {payload}")
        result = payload["result"]
        if total is None:
            total = result.get("total")
        batch = result.get("records", [])
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < limit:
            break

    df = pd.DataFrame(rows)
    df.to_csv(cfg["target_csv"], index=False)
    meta = {
        "resource_id": cfg["resource_id"],
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "downloaded_at_utc": datetime.utcnow().isoformat() + "Z",
        "total_reported": total,
    }
    write_json(cfg["target_meta"], meta)
    run_report["downloads"]["schools_directory_api"] = {
        "status": "ok",
        "rows": int(len(df)),
        "file": str(cfg["target_csv"]),
        "meta": str(cfg["target_meta"]),
    }

def download_binary(name: str, cfg: dict):
    target = cfg["target"]
    r = session.get(cfg["url"], timeout=90)
    content_type = r.headers.get("content-type", "")
    size = len(r.content)

    if r.status_code == 200 and size > 10000:
        target.write_bytes(r.content)
        run_report["downloads"][name] = {
            "status": "ok",
            "file": str(target),
            "http_status": r.status_code,
            "content_type": content_type,
            "bytes": size,
        }
    else:
        err_path = PROF / f"{name}_download_error.txt"
        err_path.write_text(
            f"URL: {cfg['url']}\n"
            f"HTTP_STATUS: {r.status_code}\n"
            f"CONTENT_TYPE: {content_type}\n"
            f"BYTES: {size}\n\n"
            f"{r.text[:4000]}"
        )
        run_report["downloads"][name] = {
            "status": "failed",
            "file": str(target),
            "http_status": r.status_code,
            "content_type": content_type,
            "bytes": size,
            "error_file": str(err_path),
        }

def profile_csv(path: Path, profile_name: str):
    df = pd.read_csv(path, nrows=1000)
    profile = {
        "file": str(path),
        "sample_row_count": int(len(df)),
        "columns": list(df.columns),
        "sample_rows": df.head(5).fillna("").astype(str).to_dict(orient="records"),
    }
    out = PROF / f"{profile_name}.json"
    write_json(out, profile)
    run_report["profiles"][profile_name] = {
        "file": str(path),
        "profile_json": str(out),
        "columns": list(df.columns),
    }

def probe_sheet(path: Path, sheet_name: str):
    raw_preview = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=8)
    candidates = []
    for header_row in range(0, 6):
        try:
            df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, nrows=5)
            cols = [str(c) for c in df.columns]
            score = sum(1 for c in cols if c and not c.lower().startswith("unnamed"))
            candidates.append({
                "header_row": header_row,
                "score": score,
                "columns": cols[:25],
                "sample_rows": df.head(3).fillna("").astype(str).to_dict(orient="records"),
            })
        except Exception as e:
            candidates.append({"header_row": header_row, "error": str(e)})

    scored = [c for c in candidates if "score" in c]
    scored.sort(key=lambda x: x["score"], reverse=True)

    return {
        "sheet_name": sheet_name,
        "raw_preview": raw_preview.fillna("").astype(str).values.tolist(),
        "best_guess": scored[0] if scored else None,
        "header_probes": candidates,
    }

def profile_xlsx(path: Path, profile_name: str):
    xl = pd.ExcelFile(path)
    sheet_profiles = []
    for sheet in xl.sheet_names[:20]:
        try:
            sheet_profiles.append(probe_sheet(path, sheet))
        except Exception as e:
            sheet_profiles.append({"sheet_name": sheet, "error": str(e)})

    profile = {
        "file": str(path),
        "sheet_count": len(xl.sheet_names),
        "sheet_names": xl.sheet_names,
        "sheet_profiles": sheet_profiles,
    }
    out = PROF / f"{profile_name}.json"
    write_json(out, profile)
    run_report["profiles"][profile_name] = {
        "file": str(path),
        "sheet_count": len(xl.sheet_names),
        "sheet_names": xl.sheet_names,
        "profile_json": str(out),
    }

def main():
    print("=== NZ SOURCE PROBE START ===")

    try:
        download_ckan_datastore()
        print("schools_directory_api: OK")
    except Exception as e:
        run_report["downloads"]["schools_directory_api"] = {"status": "failed", "error": str(e)}
        print(f"schools_directory_api: FAILED -> {e}")

    for name, cfg in SOURCES.items():
        if name == "schools_directory_api":
            continue
        try:
            download_binary(name, cfg)
            print(f"{name}: {run_report['downloads'][name]['status'].upper()}")
        except Exception as e:
            run_report["downloads"][name] = {"status": "failed", "error": str(e)}
            print(f"{name}: FAILED -> {e}")

    schools_csv = SOURCES["schools_directory_api"]["target_csv"]
    if schools_csv.exists():
        profile_csv(schools_csv, "nz_schools_directory_profile")
        print("nz_schools_directory_profile: OK")

    for name, cfg in SOURCES.items():
        if cfg["type"] == "xlsx" and cfg["target"].exists():
            try:
                profile_xlsx(cfg["target"], f"{name}_profile")
                print(f"{name}_profile: OK")
            except Exception as e:
                run_report["profiles"][f"{name}_profile"] = {"status": "failed", "error": str(e)}
                print(f"{name}_profile: FAILED -> {e}")

    write_json(PROF / "nz_probe_run_report.json", run_report)

    summary = []
    summary.append("# NZ Source Probe Summary")
    summary.append("")
    summary.append(f"Run UTC: {run_report['run_utc']}")
    summary.append("")
    summary.append("## Downloads")
    for name, meta in run_report["downloads"].items():
        summary.append(f"- {name}: {meta.get('status')}")
        for k, v in meta.items():
            if k != "status":
                summary.append(f"  - {k}: {v}")
    summary.append("")
    summary.append("## Profiles")
    for name, meta in run_report["profiles"].items():
        summary.append(f"- {name}: {meta}")

    (PROF / "nz_probe_summary.md").write_text("\n".join(summary))
    print("=== NZ SOURCE PROBE COMPLETE ===")
    print(f"SUMMARY_FILE={PROF / 'nz_probe_summary.md'}")
    print(f"RUN_REPORT={PROF / 'nz_probe_run_report.json'}")

if __name__ == "__main__":
    main()
