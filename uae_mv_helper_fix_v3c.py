#!/usr/bin/env python3
"""
uae_mv_helper_fix_v3c.py
========================
Fixes the _mv_curriculum_kpi() helper in both utils files.

ROOT CAUSE:
  _q() returns a pandas DataFrame, but the injected helper treats it like a
  plain list:
    • `if not rows:`      → raises ValueError("The truth value of a DataFrame
                             is ambiguous") → caught → returns None
    • `r = rows[0]`       → returns the FIRST COLUMN LABEL (a string), not row
    • `r[0]`, `r[1]`…    → positional access on a Series of column names → wrong

  Because the try/except swallows the ValueError, _mv_curriculum_kpi ALWAYS
  returns None, so the MV path is never taken and the fallback shows
  emirate-wide totals (e.g. 101 821 students for all Abu Dhabi curricula).

FIX:
  Replace the try-block body with DataFrame-safe access:
    rows.empty          → correct empty check
    rows.iloc[0]        → correct first-row access (named Series)
    r["col_name"]       → access by column name (NaN-safe helper)
"""

import re
import shutil
import datetime
import sys
import ast

# ── Files to patch ──────────────────────────────────────────────────────────
FILES = [
    "utils/uae_page_renderer.py",
    "utils/uae_current.py",
]

# ── Old try-block body (identical in both files, verbatim from GitHub) ──────
OLD_TRY_BODY = """\
        rows = _q(agg_sql, params)
        if not rows:
            return None
        r = rows[0]
        return {
            "school_count":       int(r[0]  or 0),
            "student_count":      r[1],          # None if no enr data
            "teacher_count":      r[2],          # None if no tch data
            "staff_count":        r[3],
            "female_students":    r[4],
            "male_students":      r[5],
            "emirati_students":   r[6],
            "resident_students":  r[7],
            "female_teachers":    r[8],
            "male_teachers":      r[9],
            "emirati_teachers":  r[10],
            "resident_teachers":  r[11],
            "has_enrollment_data": bool(r[12]),
            "has_teacher_data":   bool(r[13]),
            "row_count":          int(r[14] or 0),
        }
    except Exception:
        return None          # MV not available – caller falls back gracefully"""

# ── New try-block body (DataFrame-safe) ─────────────────────────────────────
NEW_TRY_BODY = """\
        rows = _q(agg_sql, params)
        # MV_HELPER_FIX_v3c: _q returns a DataFrame, not a list
        if rows is None or rows.empty:          # DataFrame-safe empty check
            return None
        r = rows.iloc[0]                        # first row as named Series

        def _sv(key):                           # safe scalar: NaN → None
            import math
            try:
                v = r[key]
                if v is None:
                    return None
                if isinstance(v, float) and math.isnan(v):
                    return None
                return v
            except (KeyError, TypeError):
                return None

        return {
            "school_count":        int(_sv("school_count")  or 0),
            "student_count":       _sv("student_count"),      # None if no enr data
            "teacher_count":       _sv("teacher_count"),      # None if no tch data
            "staff_count":         _sv("staff_count"),
            "female_students":     _sv("female_students"),
            "male_students":       _sv("male_students"),
            "emirati_students":    _sv("emirati_students"),
            "resident_students":   _sv("resident_students"),
            "female_teachers":     _sv("female_teachers"),
            "male_teachers":       _sv("male_teachers"),
            "emirati_teachers":    _sv("emirati_teachers"),
            "resident_teachers":   _sv("resident_teachers"),
            "has_enrollment_data": bool(_sv("has_enrollment_data") or False),
            "has_teacher_data":    bool(_sv("has_teacher_data")    or False),
            "row_count":           int(_sv("row_count") or 0),
        }
    except Exception as exc:
        print(f"[_mv_curriculum_kpi ERROR] {exc}")
        return None          # MV not available – caller falls back gracefully"""


def patch_file(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()

    if "MV_HELPER_FIX_v3c" in src:
        print(f"  ⚠️  {path}: already patched with v3c – skipped.")
        return True

    if OLD_TRY_BODY not in src:
        print(f"  ❌ {path}: OLD_TRY_BODY not found – cannot patch.")
        print("     Searching for closest match …")
        # show the surrounding context of `rows = _q(agg_sql, params)`
        idx = src.find("rows = _q(agg_sql, params)")
        if idx != -1:
            snippet = src[max(0, idx-30):idx+300]
            print("     Found context:")
            for ln in snippet.splitlines():
                print(f"       {ln}")
        return False

    # Backup
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{path}.bak_v3c_{ts}"
    shutil.copy2(path, bak)
    print(f"  ✅ backup → {bak}")

    new_src = src.replace(OLD_TRY_BODY, NEW_TRY_BODY, 1)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_src)

    # Syntax check
    try:
        ast.parse(new_src)
        print(f"  ✅ {path}: helper fixed, syntax OK.")
    except SyntaxError as e:
        print(f"  ❌ {path}: SyntaxError after patch – {e}  (restoring backup)")
        shutil.copy2(bak, path)
        return False

    return True


def main():
    print()
    print("━" * 60)
    print("  UAE MV Helper Fix v3c  (DataFrame-safe _mv_curriculum_kpi)")
    print("━" * 60)
    print()

    results = {}
    for f in FILES:
        try:
            ok = patch_file(f)
        except FileNotFoundError:
            print(f"  ❌ {f}: file not found.")
            ok = False
        results[f] = ok

    print()
    print("── Summary " + "─" * 50)
    for f, ok in results.items():
        status = "✅ OK" if ok else "❌ FAILED"
        print(f"  {f:<40} {status}")
    print()

    if all(results.values()):
        print("✅ Both files patched.  Next:")
        print("   pkill -f 'streamlit run' && sleep 2")
        print("   nohup venv/bin/streamlit run app.py \\")
        print("     --server.port 8501 --server.address 0.0.0.0 \\")
        print("     > /tmp/streamlit.log 2>&1 &")
        print("   sleep 10 && grep -iE 'error|started' /tmp/streamlit.log | tail -5")
    else:
        print("❌ One or more files could not be patched.  Check output above.")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
