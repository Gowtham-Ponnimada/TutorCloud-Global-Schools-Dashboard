#!/usr/bin/env python3
"""
uae_mv_helper_fix_v3d.py
========================
Surgical line-by-line fix for _mv_curriculum_kpi() in both utils files.

Strategy (no whole-block matching needed):
  1. Replace `        if not rows:` with DataFrame-safe check
  2. Replace `        r = rows[0]`   with `rows.iloc[0]` + NaN-unpacker
  3. Replace `    except Exception:` with logging version
     (scoped to the _mv_curriculum_kpi function only)

All replacements are ASCII-safe (no multi-byte dash matching).
"""

import re, shutil, datetime, sys, ast

FILES = [
    "utils/uae_page_renderer.py",
    "utils/uae_current.py",
]

MARKER = "MV_HELPER_FIX_v3d"

# ── Replacement 1 ────────────────────────────────────────────────────────────
# OLD:  `        if not rows:`
# NEW:  `        if rows is None or rows.empty:   # MV_HELPER_FIX_v3d`
# We scope it to the block that follows "rows = _q(agg_sql, params)"
OLD_IF   = "        if not rows:"
NEW_IF   = "        if rows is None or rows.empty:  # MV_HELPER_FIX_v3d – DataFrame-safe empty check"

# ── Replacement 2 ────────────────────────────────────────────────────────────
# OLD:  `        r = rows[0]`
# NEW:  `        r = rows.iloc[0]`  + NaN-unpacker so existing r[N] still works
OLD_R    = "        r = rows[0]"
NEW_R    = """\
        r = rows.iloc[0]  # MV_HELPER_FIX_v3d – first row of DataFrame
        # Unpack named columns into a list so existing r[N] indexing is preserved
        import math as _math
        def _sv(v):
            \"\"\"SQL NULL (pandas NaN/None) → Python None.\"\"\"
            if v is None:
                return None
            if isinstance(v, float) and _math.isnan(v):
                return None
            return v
        r = [
            _sv(r["school_count"]),        # r[0]
            _sv(r["student_count"]),        # r[1]
            _sv(r["teacher_count"]),        # r[2]
            _sv(r["staff_count"]),          # r[3]
            _sv(r["female_students"]),      # r[4]
            _sv(r["male_students"]),        # r[5]
            _sv(r["emirati_students"]),     # r[6]
            _sv(r["resident_students"]),    # r[7]
            _sv(r["female_teachers"]),      # r[8]
            _sv(r["male_teachers"]),        # r[9]
            _sv(r["emirati_teachers"]),     # r[10]
            _sv(r["resident_teachers"]),    # r[11]
            _sv(r["has_enrollment_data"]),  # r[12]
            _sv(r["has_teacher_data"]),     # r[13]
            _sv(r["row_count"]),            # r[14]
        ]"""

# ── Replacement 3 ────────────────────────────────────────────────────────────
# Replace the bare "except Exception:" that closes the _mv_curriculum_kpi try
# (identified by the line that immediately follows "        }" closing the return dict).
# We match it ONLY inside the _mv_curriculum_kpi function by replacing the
# first occurrence after "rows = _q(agg_sql, params)".
# We do a targeted str.replace on the small window between function start and end.
OLD_EXCEPT = "    except Exception:\n        return None          # MV not available \u2013 caller falls back gracefully"
NEW_EXCEPT = "    except Exception as _exc:  # MV_HELPER_FIX_v3d\n        print(f\"[_mv_curriculum_kpi ERROR] {_exc}\")\n        return None          # MV not available \u2013 caller falls back gracefully"


def patch_file(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()

    if MARKER in src:
        print(f"  \u26a0\ufe0f  {path}: already patched with v3d \u2013 skipped.")
        return True

    changed = False
    report  = []

    # ── Fix 1: `if not rows:` → DataFrame-safe ──────────────────────────────
    # Only replace if it's preceded on a nearby line by `rows = _q(agg_sql, params)`
    # Strategy: locate the window containing both lines and replace within it.
    ANCHOR = "        rows = _q(agg_sql, params)"
    if ANCHOR in src and OLD_IF in src:
        # Find the position of ANCHOR; replace OLD_IF only in the 500-char window after it
        anchor_pos = src.index(ANCHOR)
        window_end = anchor_pos + 500
        window     = src[anchor_pos:window_end]
        if OLD_IF in window:
            window_new = window.replace(OLD_IF, NEW_IF, 1)
            src = src[:anchor_pos] + window_new + src[window_end:]
            report.append("  \u2705 Fix 1: `if not rows:` \u2192 DataFrame-safe empty check")
            changed = True
        else:
            report.append("  \u26a0\ufe0f  Fix 1: OLD_IF not found within 500 chars of ANCHOR")
    else:
        report.append(f"  \u274c Fix 1: ANCHOR='{ANCHOR}' or OLD_IF not found")

    # ── Fix 2: `r = rows[0]` → iloc[0] + NaN-unpacker ───────────────────────
    if OLD_R in src:
        src = src.replace(OLD_R, NEW_R, 1)
        report.append("  \u2705 Fix 2: `r = rows[0]` \u2192 `rows.iloc[0]` + NaN-unpacker")
        changed = True
    else:
        report.append("  \u26a0\ufe0f  Fix 2: `r = rows[0]` not found (may already be patched)")

    # ── Fix 3: bare `except Exception:` → with logging ───────────────────────
    if OLD_EXCEPT in src:
        src = src.replace(OLD_EXCEPT, NEW_EXCEPT, 1)
        report.append("  \u2705 Fix 3: `except Exception:` \u2192 logging version")
        changed = True
    else:
        report.append("  \u26a0\ufe0f  Fix 3: OLD_EXCEPT pattern not found (may already be patched or different dash)")
        # Fallback: try without the dash comment
        OLD_EXCEPT_BARE = "    except Exception:\n        return None          # MV not available"
        NEW_EXCEPT_BARE = "    except Exception as _exc:  # MV_HELPER_FIX_v3d\n        print(f\"[_mv_curriculum_kpi ERROR] {_exc}\")\n        return None          # MV not available"
        if OLD_EXCEPT_BARE in src:
            src = src.replace(OLD_EXCEPT_BARE, NEW_EXCEPT_BARE, 1)
            report.append("  \u2705 Fix 3 (fallback): bare except patched via prefix match")
            changed = True

    if not changed:
        print(f"  \u274c {path}: no changes applied.")
        for r in report:
            print(r)
        return False

    # Backup
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{path}.bak_v3d_{ts}"
    shutil.copy2(path, bak)
    print(f"  \u2705 backup \u2192 {bak}")

    # Write
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)

    # Syntax check
    try:
        ast.parse(src)
        print(f"  \u2705 {path}: patched, syntax OK.")
    except SyntaxError as e:
        print(f"  \u274c {path}: SyntaxError after patch \u2013 {e}  (restoring backup)")
        shutil.copy2(bak, path)
        return False

    for r in report:
        print(r)
    return True


def main():
    print()
    print("\u2501" * 62)
    print("  UAE MV Helper Fix v3d  (line-by-line, Unicode-safe)")
    print("\u2501" * 62)
    print()

    results = {}
    for f in FILES:
        try:
            ok = patch_file(f)
        except FileNotFoundError:
            print(f"  \u274c {f}: file not found.")
            ok = False
        results[f] = ok
        print()

    print("\u2500\u2500 Summary " + "\u2500" * 52)
    for f, ok in results.items():
        status = "\u2705 OK" if ok else "\u274c FAILED"
        print(f"  {f:<42} {status}")
    print()

    if all(results.values()):
        print("\u2705 Both files patched.  Next steps:")
        print("   1. grep -n 'MV_HELPER_FIX_v3d\\|rows.iloc\\|rows.empty' utils/uae_page_renderer.py utils/uae_current.py")
        print("   2. pkill -f 'streamlit run' && sleep 2")
        print("   3. nohup venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &")
        print("   4. sleep 10 && grep -iE 'error|started' /tmp/streamlit.log | tail -5")
    else:
        print("\u274c One or more files could not be patched.")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
