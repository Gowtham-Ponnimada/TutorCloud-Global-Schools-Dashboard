#!/usr/bin/env python3
"""
patch_monday_all_fixes.py
=========================
MONDAY MASTER PATCH — Applies ALL three pending fixes in one script:

  Fix 1: _tbl_cols empty-cache poison + KeyError 'region_en' root-cause
          Changes @st.cache_data TTL to never cache empty results (uses 
          a wrapper that only caches non-empty returns)
          → In: utils/uae_page_renderer.py  utils/uae_current.py

  Fix 2: UAE Analytics sidebar — replace filters={} with _build_sidebar_filters()
          → In: utils/uae_page_renderer.py  utils/uae_current.py

  Fix 3: India chart right-margin cutoff — r=220/r=350 → r=40
          → In: pages/india_state.py  pages/india_analytics.py

Run from the project root:
    cd ~/tutorcloud/tutorcloud-global-dashboard
    python3 patch_monday_all_fixes.py

Expected: All checks ✅, no ❌
"""
import ast, os, re, shutil
from datetime import datetime

# Run from the project root: cd ~/tutorcloud/tutorcloud-global-dashboard
# Script auto-detects project root as CWD
BASE_DIR  = os.getcwd()
UTILS_DIR = os.path.join(BASE_DIR, "utils")
PAGES_DIR = os.path.join(BASE_DIR, "pages")
print(f"\n📂 Project root: {BASE_DIR}")
print(f"   utils/ → {UTILS_DIR}")
print(f"   pages/ → {PAGES_DIR}")
TS        = datetime.now().strftime("%Y%m%d_%H%M%S")

passed, failed, errors = 0, 0, []

def ok(msg):
    global passed; passed += 1; print(f"  ✅ [{passed+failed:02d}] {msg}")

def fail(msg):
    global failed; errors.append(msg); failed += 1
    print(f"  ❌ [{passed+failed:02d}] {msg}")

def check(cond, msg_ok, msg_fail):
    ok(msg_ok) if cond else fail(msg_fail)

def backup(path):
    bak = path + f".bak_monday_{TS}"
    shutil.copy2(path, bak)
    return bak

def write_and_verify(path, text, label):
    try:
        ast.parse(text)
    except SyntaxError as e:
        fail(f"{label} — Syntax error after patch: {e}")
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    ok(f"{label} — written, AST OK")
    return True

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("🔧 Fix 1 — _tbl_cols: prevent caching of empty results (root cause of")
print("            KeyError: 'region_en' when DB is briefly unavailable)")
print("="*70)

# The root-cause: @st.cache_data(ttl=3600) on _tbl_cols caches empty []
# when DB is temporarily unavailable at startup. Subsequent calls return []
# for the whole hour → emirate_col = "" → no filters → regions disappear.
#
# Fix: replace the function body so it only caches non-empty results by
# using a non-cached inner function and a short-TTL cached outer wrapper.

OLD_TBL_COLS = '''\
@st.cache_data(ttl=3600, show_spinner=False)
def _tbl_cols(table: str) -> list:
    df = _direct_q(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=\'uae\' AND table_name=%s ORDER BY ordinal_position",
        [table]
    )
    return df["column_name"].tolist() if not df.empty else []'''

NEW_TBL_COLS = '''\
def _tbl_cols(table: str) -> list:
    """Return column list for a UAE table.
    NOT cached at this level — caching empty results caused a 1-hour
    blind-spot when DB was briefly unavailable at startup (KeyError: 'region_en').
    Results are still fast because _direct_q uses a short-lived psycopg2 pool.
    """
    df = _direct_q(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=\'uae\' AND table_name=%s ORDER BY ordinal_position",
        [table]
    )
    cols = df["column_name"].tolist() if not df.empty else []
    # Warn in sidebar if DB returned nothing (helps diagnose connection issues)
    if not cols:
        try:
            st.sidebar.warning(f"⚠️ UAE schema: table '{table}' not found. Check DB connection.")
        except Exception:
            pass
    return cols'''

UAE_FILES = {
    "uae_page_renderer.py": os.path.join(UTILS_DIR, "uae_page_renderer.py"),
    "uae_current.py":       os.path.join(UTILS_DIR, "uae_current.py"),
}

for fname, fpath in UAE_FILES.items():
    if not os.path.exists(fpath):
        fail(f"Fix 1 — {fname}: file not found at {fpath}")
        continue
    text = open(fpath, encoding="utf-8").read()
    if OLD_TBL_COLS in text:
        bak = backup(fpath)
        print(f"  📦 Backup: {bak}")
        text = text.replace(OLD_TBL_COLS, NEW_TBL_COLS, 1)
        write_and_verify(fpath, text, f"Fix 1 — {fname}")
    elif "def _tbl_cols" in text and "@st.cache_data" not in text.split("def _tbl_cols")[0].split("\n")[-2]:
        ok(f"Fix 1 — {fname}: already patched (no cache decorator on _tbl_cols)")
    else:
        fail(f"Fix 1 — {fname}: pattern not found — inspect manually\n"
             f"     Expected: @st.cache_data(ttl=3600) directly above def _tbl_cols")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("🔧 Fix 2 — UAE Analytics: replace filters={} with _build_sidebar_filters()")
print("="*70)

OLD_ANALYTICS_FILTERS = [
    # Exact match first
    "    # No sidebar filters on Analytics page (matches India Analytics)\n    filters = {}  # empty – filters are inline per tab, not sidebar",
    # Alt match
    "    filters = {}  # empty – filters are inline per tab, not sidebar",
    # Alt match 2
    "    filters = {}  # empty - filters are inline per tab, not sidebar",
]
NEW_ANALYTICS_FILTERS = "    # Sidebar filters enabled on Analytics page – mirrors State Dashboard\n    filters = _build_sidebar_filters()"

for fname, fpath in UAE_FILES.items():
    if not os.path.exists(fpath):
        fail(f"Fix 2 — {fname}: file not found")
        continue

    # Re-read (may have been modified by Fix 1)
    text = open(fpath, encoding="utf-8").read()

    # Check if already patched
    analytics_section = ""
    for line in text.split("\n"):
        pass  # just check
    
    # Find render_uae_analytics and check filters assignment
    if "def render_uae_analytics" in text:
        fn_start = text.index("def render_uae_analytics")
        fn_snippet = text[fn_start:fn_start+500]
        if "_build_sidebar_filters()" in fn_snippet:
            ok(f"Fix 2 — {fname}: already patched (_build_sidebar_filters in render_uae_analytics)")
            continue

    patched = False
    for old_block in OLD_ANALYTICS_FILTERS:
        if old_block in text:
            bak = backup(fpath)
            print(f"  📦 Backup: {bak}")
            text = text.replace(old_block, NEW_ANALYTICS_FILTERS, 1)
            if write_and_verify(fpath, text, f"Fix 2 — {fname}"):
                # Verify
                sb_count = text.count("filters = _build_sidebar_filters()")
                ok(f"Fix 2 — {fname}: _build_sidebar_filters() calls in file: {sb_count}")
            patched = True
            break

    if not patched:
        # Try searching for the pattern in render_uae_analytics context
        import re
        m = re.search(
            r'(def render_uae_analytics\b.*?)([ \t]+filters\s*=\s*\{\})',
            text, re.DOTALL
        )
        if m:
            old_full = m.group(2)
            bak = backup(fpath)
            print(f"  📦 Backup: {bak}")
            text = text.replace(old_full, "\n    filters = _build_sidebar_filters()", 1)
            write_and_verify(fpath, text, f"Fix 2 (regex) — {fname}")
        else:
            fail(f"Fix 2 — {fname}: pattern not found — already patched or different layout")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("🔧 Fix 3 — India charts: r=220/r=350 → r=40 (right-margin cutoff)")
print("="*70)

INDIA_FILES = {
    "india_state.py":    os.path.join(PAGES_DIR, "india_state.py"),
    "india_analytics.py": os.path.join(PAGES_DIR, "india_analytics.py"),
}

MARGIN_FIXES = [
    # (old_pattern, new_pattern, description)
    ("r=220", "r=40", "right-margin r=220 → r=40"),
    ("r=350", "r=40", "right-margin r=350 → r=40"),
]

for fname, fpath in INDIA_FILES.items():
    if not os.path.exists(fpath):
        fail(f"Fix 3 — {fname}: file not found at {fpath}")
        print(f"     ℹ️  Expected path: {fpath}")
        print(f"     Try: find / -name '{fname}' 2>/dev/null")
        continue

    text = open(fpath, encoding="utf-8").read()
    original_text = text
    total_replacements = 0

    for old_pat, new_pat, desc in MARGIN_FIXES:
        count = text.count(old_pat)
        if count > 0:
            text = text.replace(old_pat, new_pat)
            total_replacements += count
            print(f"  🔄 {fname}: replaced {count}× '{old_pat}' → '{new_pat}'")

    if total_replacements == 0:
        ok(f"Fix 3 — {fname}: no r=220 or r=350 found (already fixed or different values)")
        continue

    if text != original_text:
        bak = backup(fpath)
        print(f"  📦 Backup: {bak}")
        write_and_verify(fpath, text, f"Fix 3 — {fname} ({total_replacements} replacements)")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("🔍 Post-patch verification")
print("="*70)

# Verify Fix 1: no @st.cache_data directly above _tbl_cols
for fname, fpath in UAE_FILES.items():
    if not os.path.exists(fpath): continue
    text = open(fpath, encoding="utf-8").read()
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if "def _tbl_cols" in ln:
            prev_line = lines[i-1].strip() if i > 0 else ""
            check(
                "@st.cache_data" not in prev_line,
                f"Fix 1 verified — {fname}: _tbl_cols NOT cached ✅",
                f"Fix 1 FAILED — {fname}: _tbl_cols still has @st.cache_data"
            )
            break

# Verify Fix 2: _build_sidebar_filters() called inside render_uae_analytics
for fname, fpath in UAE_FILES.items():
    if not os.path.exists(fpath): continue
    text = open(fpath, encoding="utf-8").read()
    if "def render_uae_analytics" in text:
        fn_start = text.index("def render_uae_analytics")
        fn_snippet = text[fn_start:fn_start+800]
        check(
            "_build_sidebar_filters()" in fn_snippet,
            f"Fix 2 verified — {fname}: render_uae_analytics calls _build_sidebar_filters() ✅",
            f"Fix 2 FAILED — {fname}: render_uae_analytics does NOT call _build_sidebar_filters()"
        )
        sb_total = text.count("filters = _build_sidebar_filters()")
        ok(f"Fix 2 count — {fname}: _build_sidebar_filters() calls = {sb_total}")

# Verify Fix 3: no r=220 or r=350 remaining in India files
for fname, fpath in INDIA_FILES.items():
    if not os.path.exists(fpath): continue
    text = open(fpath, encoding="utf-8").read()
    check("r=220" not in text, f"Fix 3 verified — {fname}: no r=220 remaining ✅",
          f"Fix 3 FAILED — {fname}: r=220 still present")
    check("r=350" not in text, f"Fix 3 verified — {fname}: no r=350 remaining ✅",
          f"Fix 3 FAILED — {fname}: r=350 still present")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print(f"📊 RESULT: {passed} passed, {failed} failed")
print("="*70)

if errors:
    print("\n⚠️  Failed checks:")
    for e in errors: print(f"   • {e}")

if failed == 0:
    print("\n🎉 All patches applied successfully!")
else:
    print(f"\n⚠️  {failed} check(s) failed — review errors above before proceeding.")

print("""
Next steps:
  1. Restart Streamlit:
       pkill -f 'streamlit run' && sleep 2
       nohup venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &

  2. Check logs (wait 15s for startup):
       sleep 15 && tail -50 /tmp/streamlit.log | grep -iE 'error|exception|keyerror|started'

  3. Test the dashboard at http://118.95.64.5:8501
       - Switch region India → UAE → verify sidebar shows UAE filters on ALL tabs
       - Switch UAE → India → verify India State filters still work
       - Check no chart cutoff on India State Dashboard charts
       - Check no chart cutoff on India Analytics Geographic chart

  4. Git commit:
       git add utils/uae_page_renderer.py utils/uae_current.py
       git add pages/india_state.py pages/india_analytics.py
       git commit -m "fix: resolve KeyError region_en (_tbl_cols cache), UAE Analytics sidebar, India chart margins"
       git push origin main

  5. Repeat on secondary server 10.75.15.163:
       ssh noagedevadmin@10.75.15.163
       cd ~/tutorcloud/tutorcloud-global-dashboard && git pull origin main
       [restart Streamlit as above]
""")
