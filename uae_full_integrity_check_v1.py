#!/usr/bin/env python3
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

DB_PARAMS = dict(
    host="localhost",
    dbname="tutorcloud_db",
    user="tutorcloud_admin",
    password="TutorCloud2024!Secure",
)
UAE_YEAR = "2024-2025"
REPORT_ROOT = Path("integrity_reports")


class DB:
    def __enter__(self):
        self.conn = psycopg2.connect(**DB_PARAMS)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.conn.close()
        except Exception:
            pass

    def rows(self, sql, params=None):
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            return [dict(r) for r in cur.fetchall()]

    def scalar(self, sql, params=None, default=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params or [])
            row = cur.fetchone()
            return default if not row else row[0]


def pick_col(cols, *candidates):
    for c in candidates:
        if c in cols:
            return c
    return ""


def get_cols(db, table):
    rows = db.rows(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='uae' AND table_name=%s ORDER BY ordinal_position",
        [table],
    )
    return [r["column_name"] for r in rows]


def distinct(db, table, col):
    if not col:
        return []
    rows = db.rows(
        f"SELECT DISTINCT {col} AS v FROM uae.{table} "
        f"WHERE academic_year=%s AND {col} IS NOT NULL ORDER BY 1",
        [UAE_YEAR],
    )
    out = []
    for r in rows:
        v = r["v"]
        s = str(v).strip() if v is not None else ""
        if s:
            out.append(s)
    return out


def union_distinct(db, pairs):
    seen = set()
    out = []
    for table, col in pairs:
        for v in distinct(db, table, col):
            if v not in seen:
                seen.add(v)
                out.append(v)
    return sorted(out, key=lambda x: x.lower())


def get_cfg(db):
    enr_cols = get_cols(db, "uae_fact_enrollment")
    sch_cols = get_cols(db, "uae_fact_schools")
    tch_cols = get_cols(db, "uae_fact_teachers_emirate")
    pf_cols = get_cols(db, "uae_fact_pass_fail")
    sc_cols = get_cols(db, "uae_fact_student_scores")
    nat_cols = get_cols(db, "uae_fact_student_nationalities")

    cfg = {
        "enr": {
            "table": "uae_fact_enrollment",
            "cols": enr_cols,
            "emirate": pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region"),
            "education_type": pick_col(enr_cols, "education_type", "school_type", "edu_type", "type"),
            "gender": pick_col(enr_cols, "gender", "student_gender"),
            "nationality": pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality"),
            "count": pick_col(enr_cols, "student_count", "enrollment_count", "students", "count"),
        },
        "sch": {
            "table": "uae_fact_schools",
            "cols": sch_cols,
            "emirate": pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region"),
            "education_type": pick_col(sch_cols, "education_type", "school_type", "edu_type", "type"),
            "curriculum": pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type"),
            "gender": pick_col(sch_cols, "gender", "school_gender"),
            "count": pick_col(sch_cols, "school_count", "num_schools", "count"),
        },
        "tch": {
            "table": "uae_fact_teachers_emirate",
            "cols": tch_cols,
            "emirate": pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region"),
            "education_type": pick_col(tch_cols, "education_type", "school_type", "edu_type", "type"),
            "gender": pick_col(tch_cols, "gender", "teacher_gender"),
            "count": pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers"),
        },
        "pf": {
            "table": "uae_fact_pass_fail",
            "cols": pf_cols,
            "emirate": pick_col(pf_cols, "region_en", "emirate", "emirate_en", "region"),
            "education_type": pick_col(pf_cols, "education_type", "school_type", "edu_type", "type"),
            "gender": pick_col(pf_cols, "gender", "student_gender"),
        },
        "sc": {
            "table": "uae_fact_student_scores",
            "cols": sc_cols,
            "emirate": pick_col(sc_cols, "region_en", "emirate", "emirate_en", "region"),
            "education_type": pick_col(sc_cols, "education_type", "school_type", "edu_type", "type"),
            "gender": pick_col(sc_cols, "gender", "student_gender"),
            "avg": pick_col(sc_cols, "average_score", "avg_score", "score", "mean_score"),
        },
        "nat": {
            "table": "uae_fact_student_nationalities",
            "cols": nat_cols,
            "emirate": pick_col(nat_cols, "region_en", "emirate", "emirate_en", "region"),
            "gender": pick_col(nat_cols, "gender", "student_gender"),
            "nationality": pick_col(nat_cols, "nationality_cat", "nationality_category", "nationality"),
            "count": pick_col(nat_cols, "student_count", "count", "students"),
        },
    }
    return cfg


def add_in(parts, params, col, values):
    if not values:
        parts.append("1=0")
        return
    placeholders = ",".join(["%s"] * len(values))
    parts.append(f"{col} IN ({placeholders})")
    params.extend(values)


def curriculum_emirates(db, cfg, curriculum_val):
    sch = cfg["sch"]
    if not (sch["curriculum"] and sch["emirate"]):
        return []
    rows = db.rows(
        f"SELECT DISTINCT {sch['emirate']} AS v FROM uae.{sch['table']} "
        f"WHERE academic_year=%s AND {sch['curriculum']}=%s ORDER BY 1",
        [UAE_YEAR, curriculum_val],
    )
    return [str(r["v"]).strip() for r in rows if r["v"] is not None and str(r["v"]).strip()]


def build_where(db, cfg, table_key, flt):
    c = cfg[table_key]
    parts = ["academic_year=%s"]
    params = [UAE_YEAR]

    if flt.get("emirate") and c.get("emirate"):
        parts.append(f"{c['emirate']}=%s")
        params.append(flt["emirate"])

    if flt.get("education_type") and c.get("education_type"):
        parts.append(f"{c['education_type']}=%s")
        params.append(flt["education_type"])

    if flt.get("gender") and table_key in ("enr", "pf", "sc", "nat") and c.get("gender"):
        parts.append(f"{c['gender']}=%s")
        params.append(flt["gender"])

    if flt.get("nationality") and table_key in ("enr", "nat") and c.get("nationality"):
        parts.append(f"{c['nationality']}=%s")
        params.append(flt["nationality"])

    if flt.get("curriculum"):
        if table_key == "sch" and c.get("curriculum"):
            parts.append(f"{c['curriculum']}=%s")
            params.append(flt["curriculum"])
        elif c.get("emirate"):
            ems = curriculum_emirates(db, cfg, flt["curriculum"])
            add_in(parts, params, c["emirate"], ems)
        else:
            parts.append("1=0")

    return " WHERE " + " AND ".join(parts), params


def scalar_sum(db, table, col, where, params):
    if not col:
        return None
    return db.scalar(f"SELECT COALESCE(SUM({col}),0) FROM uae.{table}{where}", params, default=0)


def scalar_count(db, table, where, params):
    return db.scalar(f"SELECT COUNT(*) FROM uae.{table}{where}", params, default=0)


def scalar_avg(db, table, col, where, params):
    if not col:
        return None
    return db.scalar(f"SELECT AVG({col}) FROM uae.{table}{where}", params, default=None)


def case_key(flt):
    order = ["emirate", "education_type", "gender", "nationality", "curriculum"]
    parts = [f"{k}={flt[k]}" for k in order if flt.get(k)]
    return " | ".join(parts) if parts else "UNFILTERED"


def metrics_for_case(db, cfg, flt):
    out = {
        "case": case_key(flt),
        **{k: flt.get(k, "") for k in ["emirate", "education_type", "gender", "nationality", "curriculum"]}
    }

    we, pe = build_where(db, cfg, "enr", flt)
    ws, ps = build_where(db, cfg, "sch", flt)
    wt, pt = build_where(db, cfg, "tch", flt)
    wp, pp = build_where(db, cfg, "pf", flt)
    wc, pc = build_where(db, cfg, "sc", flt)
    wn, pn = build_where(db, cfg, "nat", flt)

    out["students"] = int(scalar_sum(db, cfg["enr"]["table"], cfg["enr"]["count"], we, pe) or 0)
    out["schools"] = int(scalar_sum(db, cfg["sch"]["table"], cfg["sch"]["count"], ws, ps) or 0)
    out["teachers"] = int(scalar_sum(db, cfg["tch"]["table"], cfg["tch"]["count"], wt, pt) or 0)
    out["pf_rows"] = int(scalar_count(db, cfg["pf"]["table"], wp, pp) or 0)
    out["score_rows"] = int(scalar_count(db, cfg["sc"]["table"], wc, pc) or 0)
    out["nat_rows"] = int(scalar_count(db, cfg["nat"]["table"], wn, pn) or 0)
    avg_score = scalar_avg(db, cfg["sc"]["table"], cfg["sc"]["avg"], wc, pc)
    out["avg_score"] = round(float(avg_score), 4) if avg_score is not None else None
    out["ptr"] = round(out["students"] / out["teachers"], 4) if out["teachers"] else None
    return out


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = REPORT_ROOT / f"uae_integrity_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)
    failures = []
    metrics_rows = []
    counters = Counter()

    with DB() as db:
        cfg = get_cfg(db)

        # Code integrity checks
        for rel, marker in [
            ("utils/uae_page_renderer.py", "UAE_FILTER_FRAMEWORK_FIX_v1"),
            ("utils/uae_current.py", "UAE_FILTER_FRAMEWORK_FIX_v1"),
            ("utils/uae_page_renderer.py", "UAE_GENDER_SCOPE_FIX_v2"),
            ("utils/uae_current.py", "UAE_GENDER_SCOPE_FIX_v2"),
        ]:
            txt = read_text(rel)
            ok = marker in txt
            counters["code_checks"] += 1
            if not ok:
                failures.append({"type": "CODE_MARKER_MISSING", "case": rel, "detail": marker})
                counters["failures"] += 1
            else:
                counters["passes"] += 1

        # Filter domains from DB
        emirates = distinct(db, cfg["enr"]["table"], cfg["enr"]["emirate"])
        edu_types = union_distinct(db, [
            (cfg["enr"]["table"], cfg["enr"]["education_type"]),
            (cfg["sch"]["table"], cfg["sch"]["education_type"]),
            (cfg["tch"]["table"], cfg["tch"]["education_type"]),
            (cfg["pf"]["table"], cfg["pf"]["education_type"]),
        ])
        genders = [g for g in distinct(db, cfg["enr"]["table"], cfg["enr"]["gender"]) if g.lower() in ("male", "female")]
        nationalities = distinct(db, cfg["enr"]["table"], cfg["enr"]["nationality"])
        curricula = distinct(db, cfg["sch"]["table"], cfg["sch"]["curriculum"])

        manifest = {
            "year": UAE_YEAR,
            "counts": {
                "emirates": len(emirates),
                "education_types": len(edu_types),
                "genders": len(genders),
                "nationalities": len(nationalities),
                "curricula": len(curricula),
            },
            "values": {
                "emirates": emirates,
                "education_types": edu_types,
                "genders": genders,
                "nationalities": nationalities,
                "curricula": curricula,
            },
        }
        (outdir / "filter_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Union sanity check
        if len(edu_types) < 3:
            failures.append({"type": "EDU_TYPE_UNION_TOO_SMALL", "case": "GLOBAL", "detail": str(edu_types)})
            counters["failures"] += 1
        else:
            counters["passes"] += 1

        # Base case families
        base_cases = [dict()]
        base_cases += [{"emirate": v} for v in emirates]
        base_cases += [{"education_type": v} for v in edu_types]
        base_cases += [{"curriculum": v} for v in curricula]
        base_cases += [{"nationality": v} for v in nationalities]

        # Existing actual school triplets
        sch = cfg["sch"]
        if sch["emirate"] and sch["education_type"] and sch["curriculum"]:
            rows = db.rows(
                f"SELECT DISTINCT {sch['emirate']} AS emirate, {sch['education_type']} AS education_type, {sch['curriculum']} AS curriculum "
                f"FROM uae.{sch['table']} WHERE academic_year=%s ORDER BY 1,2,3",
                [UAE_YEAR],
            )
            base_cases += [
                {
                    "emirate": str(r["emirate"]).strip(),
                    "education_type": str(r["education_type"]).strip(),
                    "curriculum": str(r["curriculum"]).strip(),
                }
                for r in rows
                if r["emirate"] is not None and r["education_type"] is not None and r["curriculum"] is not None
            ]

        # Deduplicate cases
        seen = set()
        deduped = []
        for flt in base_cases:
            key = tuple(sorted(flt.items()))
            if key not in seen:
                seen.add(key)
                deduped.append(flt)
        base_cases = deduped

        for flt in base_cases:
            counters["base_cases"] += 1
            m0 = metrics_for_case(db, cfg, flt)
            metrics_rows.append(m0)

            # Non-negative checks across all source tables
            for fld in ["students", "schools", "teachers", "pf_rows", "score_rows", "nat_rows"]:
                if m0[fld] < 0:
                    failures.append({"type": "NEGATIVE_METRIC", "case": m0["case"], "detail": f"{fld}={m0[fld]}"})
                    counters["failures"] += 1

            # Gender checks
            if genders:
                gm = {}
                for g in genders:
                    fltg = dict(flt)
                    fltg["gender"] = g
                    mg = metrics_for_case(db, cfg, fltg)
                    metrics_rows.append(mg)
                    gm[g] = mg
                    counters["gender_cases"] += 1

                    # Gender should NOT leak into schools / teachers
                    if mg["schools"] != m0["schools"]:
                        failures.append({
                            "type": "GENDER_LEAKS_INTO_SCHOOLS",
                            "case": mg["case"],
                            "detail": f"base={m0['schools']} filtered={mg['schools']}"
                        })
                        counters["failures"] += 1

                    if mg["teachers"] != m0["teachers"]:
                        failures.append({
                            "type": "GENDER_LEAKS_INTO_TEACHERS",
                            "case": mg["case"],
                            "detail": f"base={m0['teachers']} filtered={mg['teachers']}"
                        })
                        counters["failures"] += 1

                if set(gm.keys()) >= {"Male", "Female"}:
                    split_total = gm["Male"]["students"] + gm["Female"]["students"]
                    if split_total != m0["students"]:
                        failures.append({
                            "type": "STUDENT_GENDER_PARTITION_MISMATCH",
                            "case": m0["case"],
                            "detail": f"base={m0['students']} male+female={split_total}"
                        })
                        counters["failures"] += 1
                    else:
                        counters["passes"] += 1

        # Output files
        with (outdir / "metrics.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "case", "emirate", "education_type", "gender", "nationality", "curriculum",
                "students", "schools", "teachers", "ptr", "pf_rows", "score_rows", "nat_rows", "avg_score"
            ])
            writer.writeheader()
            writer.writerows(metrics_rows)

        with (outdir / "failures.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["type", "case", "detail"])
            writer.writeheader()
            writer.writerows(failures)

        summary = {
            "year": UAE_YEAR,
            "report_dir": str(outdir),
            "base_cases": counters["base_cases"],
            "gender_cases": counters["gender_cases"],
            "code_checks": counters["code_checks"],
            "passes": counters["passes"],
            "failures": counters["failures"],
            "failure_types": dict(Counter(x["type"] for x in failures)),
        }
        (outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print("=" * 78)
        print("UAE DASHBOARD FULL DATA INTEGRITY CHECK")
        print("=" * 78)
        print(f"Year: {UAE_YEAR}")
        print(f"Report folder: {outdir}")
        print(f"Base cases checked: {counters['base_cases']}")
        print(f"Gender variant cases checked: {counters['gender_cases']}")
        print(f"Total failures: {counters['failures']}")

        if failures:
            print("\nTop failure counts:")
            for k, v in Counter(x["type"] for x in failures).most_common(10):
                print(f"- {k}: {v}")
            print(f"\nSee detailed CSV: {outdir / 'failures.csv'}")
        else:
            print("\n✅ No integrity failures detected.")

        print(f"Metrics CSV: {outdir / 'metrics.csv'}")
        print(f"Summary JSON: {outdir / 'summary.json'}")


if __name__ == "__main__":
    main()
