#!/usr/bin/env python3
"""
Region Filter Consistency Diagnostic
Run from ~/tutorcloud/tutorcloud-global-dashboard/ on the production server.

Reports exactly what render_region_badge version is installed and whether 
the region selector will appear consistently on all pages for both regions.
"""
import os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# File paths - adjust if your structure differs
PATHS = {
    "ui_styles.py":          os.path.join(BASE, "ui_styles.py"),
    "Home":                  os.path.join(BASE, "pages", "1_🏠_Home.py"),
    "State Dashboard":       os.path.join(BASE, "pages", "2_📊_State_Dashboard.py"),
    "Analytics":             os.path.join(BASE, "pages", "4_📈_Analytics.py"),
    "uae_page_renderer":     os.path.join(BASE, "utils", "uae_page_renderer.py"),
    "uae_current":           os.path.join(BASE, "utils", "uae_current.py"),
}

SEP  = "─" * 70
SEP2 = "═" * 70

def read(path):
    try:
        return open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return None

def check_mark(ok):
    return "✅" if ok else "❌"

def warn_mark(ok):
    return "✅" if ok else "⚠️ "

print(f"\n{SEP2}")
print("  REGION FILTER CONSISTENCY DIAGNOSTIC")
print(f"  Running from: {BASE}")
print(f"{SEP2}\n")

# ─────────────────────────────────────────────────────────────
# 1. ui_styles.py  –  what version of render_region_badge is installed?
# ─────────────────────────────────────────────────────────────
print(f"{SEP}")
print("  [1] ui_styles.py — render_region_badge() version check")
print(SEP)

ui_src = read(PATHS["ui_styles.py"])
if ui_src is None:
    print(f"  {check_mark(False)} NOT FOUND at {PATHS['ui_styles.py']}")
    print("  → Cannot continue without ui_styles.py")
    sys.exit(1)

ui_lines = ui_src.splitlines()
print(f"  File size : {len(ui_lines)} lines")

# Version detection
versions = {
    "v4d (try/except dedup)":      "render_region_badge v4d",
    "v4c (thread-ID dedup BROKEN)":"render_region_badge v4c",
    "v4b (st-key CSS)":            "render_region_badge v4b",
    "v4a (aria-label CSS)":        "render_region_badge v4",
    "V3/JS navigation":            "window.parent.location",
}
found_version = "UNKNOWN / NOT FOUND"
for label, marker in versions.items():
    if marker in ui_src:
        found_version = label
        break

version_ok = "v4d" in found_version
print(f"  Version   : {found_version}  {check_mark(version_ok)}")

# Key features
has_sidebar_sel  = "with st.sidebar:" in ui_src and "tc_region_selector" in ui_src
has_try_except   = "except Exception" in ui_src or "except StreamlitAPIException" in ui_src
has_thread_dedup = "_BADGE_SEEN_THREADS" in ui_src
has_rerun        = "st.rerun()" in ui_src
has_html_badge   = "position:fixed" in ui_src
has_qp_compat    = "_qp_get" in ui_src and "_qp_set" in ui_src

print(f"\n  Feature checks:")
print(f"    Sidebar selectbox present  : {check_mark(has_sidebar_sel)}")
print(f"    try/except dedup (good)    : {check_mark(has_try_except)}")
print(f"    Thread-ID dedup (broken)   : {warn_mark(not has_thread_dedup)} {'PROBLEM - will cause selector to vanish!' if has_thread_dedup else 'Not present (good)'}")
print(f"    st.rerun() on change       : {check_mark(has_rerun)}")
print(f"    Fixed HTML badge           : {check_mark(has_html_badge)}")
print(f"    Query-params compat        : {check_mark(has_qp_compat)}")

# Find definition line
def_line = next((i+1 for i,l in enumerate(ui_lines)
                 if re.match(r"^def render_region_badge\b", l)), None)
if def_line:
    print(f"  Defined at line : {def_line}")
else:
    print(f"  {check_mark(False)} render_region_badge() NOT DEFINED in ui_styles.py!")

REGION_OPTIONS_present = "REGION_OPTIONS" in ui_src and "_VALID_REGIONS" in ui_src
print(f"  REGION_OPTIONS  : {check_mark(REGION_OPTIONS_present)}")

# ─────────────────────────────────────────────────────────────
# 2. Page files – bootstrap pattern audit
# ─────────────────────────────────────────────────────────────
PAGE_FILES = ["Home", "State Dashboard", "Analytics"]

print(f"\n{SEP}")
print("  [2] Page files — bootstrap + execution order audit")
print(SEP)

page_results = {}
for page_name in PAGE_FILES:
    path = PATHS[page_name]
    src  = read(path)
    print(f"\n  PAGE: {page_name}")
    if src is None:
        print(f"    {check_mark(False)} File not found: {path}")
        page_results[page_name] = {"ok": False, "reason": "file not found"}
        continue

    lines = src.splitlines()
    print(f"    Lines : {len(lines)}")

    # set_page_config
    cfg_line = next((i+1 for i,l in enumerate(lines) if "st.set_page_config" in l), None)
    # _render_rb() call (the actual badge call)
    rb_line  = next((i+1 for i,l in enumerate(lines) if re.search(r"_render_rb\s*\(\)", l)), None)
    # UAE routing
    uae_line = next((i+1 for i,l in enumerate(lines) if "render_uae_" in l and "import" not in l), None)
    stop_line= next((i+1 for i,l in enumerate(lines) if "st.stop()" in l), None)

    cfg_ok   = cfg_line is not None
    rb_ok    = rb_line  is not None
    order_ok = cfg_ok and rb_ok and cfg_line < rb_line
    uae_ok   = uae_line is not None
    # Badge must be called BEFORE UAE routing (so UAE pages show the selector too)
    badge_before_uae = rb_ok and uae_ok and rb_line < uae_line

    print(f"    set_page_config at line   : {cfg_line}  {check_mark(cfg_ok)}")
    print(f"    render_region_badge call  : {rb_line}   {check_mark(rb_ok)}")
    print(f"    badge BEFORE page_config  : {check_mark(order_ok)}")
    print(f"    UAE routing present       : {check_mark(uae_ok)}")
    print(f"    badge BEFORE UAE routing  : {check_mark(badge_before_uae)}")

    # Import check
    has_import = "render_region_badge" in src and "import" in src
    print(f"    render_region_badge import: {check_mark(has_import)}")

    # v_final bootstrap present
    has_vfinal = "Region bootstrap v_final" in src
    print(f"    v_final bootstrap block   : {check_mark(has_vfinal)}")

    # Check which UAE function is called
    uae_func = None
    for l in lines:
        m = re.search(r"(render_uae_\w+)\s*\(\)", l)
        if m and "import" not in l:
            uae_func = m.group(1)
            break
    print(f"    UAE render function       : {uae_func or 'NOT FOUND'}")

    all_ok = all([cfg_ok, rb_ok, order_ok, uae_ok, badge_before_uae, has_import, has_vfinal])
    page_results[page_name] = {"ok": all_ok, "rb_line": rb_line, "uae_line": uae_line}
    print(f"    {'─'*40}")
    print(f"    OVERALL: {check_mark(all_ok)} {'All checks pass' if all_ok else 'Issues found — see above'}")

# ─────────────────────────────────────────────────────────────
# 3. UAE renderer – does it have its own region selector?
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  [3] UAE page renderer — region selector audit")
print(SEP)

for key in ["uae_page_renderer", "uae_current"]:
    path = PATHS[key]
    src  = read(path)
    fname = os.path.basename(path)
    print(f"\n  FILE: {fname}")
    if src is None:
        print(f"    {check_mark(False)} Not found: {path}")
        continue
    print(f"    Lines : {len(src.splitlines())}")

    has_own_badge   = "render_region_badge" in src
    has_tc_selector = "tc_region_selector" in src
    has_build_sf    = "_build_sidebar_filters" in src
    
    # Count _build_sidebar_filters calls (not definition)
    sf_calls = len(re.findall(r"filters\s*=\s*_build_sidebar_filters\(\)", src))
    sf_total = src.count("_build_sidebar_filters")

    print(f"    Has own render_region_badge : {warn_mark(not has_own_badge)} {'YES – potential duplicate!' if has_own_badge else 'No (correct)'}")
    print(f"    Has tc_region_selector key  : {warn_mark(not has_tc_selector)} {'YES – potential DuplicateWidgetID!' if has_tc_selector else 'No (correct)'}")
    print(f"    _build_sidebar_filters def  : {check_mark(has_build_sf)}")
    print(f"    filters=_build_sidebar_filters() calls: {sf_calls}")
    print(f"    Total _build_sidebar_filters refs     : {sf_total}")

    # Check which pages call _build_sidebar_filters
    for func_name in ["render_uae_home", "render_uae_state_dashboard", "render_uae_analytics"]:
        start = src.find(f"def {func_name}(")
        if start == -1:
            continue
        # Find end of this function (next top-level def)
        next_def = re.search(r"\ndef [a-zA-Z_]", src[start+len(func_name):])
        end = start + len(func_name) + next_def.start() if next_def else len(src)
        func_src = src[start:end]
        calls_sf = "_build_sidebar_filters()" in func_src
        print(f"    {func_name}: _build_sidebar_filters = {check_mark(calls_sf)} {'YES' if calls_sf else 'NO (no sidebar filters)'}")

# ─────────────────────────────────────────────────────────────
# 4. Sidebar rendering prediction
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  [4] Sidebar content prediction (what user actually sees)")
print(SEP)
print("""
  ┌─────────────────────┬──────────────────────────────────────────────┐
  │ Page / Region       │ Expected sidebar content                     │
  ├─────────────────────┼──────────────────────────────────────────────┤
  │ Home  / India       │ [Region selector] only                       │
  │ Home  / UAE         │ [Region selector] only                       │
  │ State / India       │ [Region selector] + State/District/Block     │
  │ State / UAE         │ [Region selector] + 5 UAE filters            │
  │ Analytics / India   │ [Region selector] + inline tab selectors     │
  │ Analytics / UAE     │ [Region selector] + 5 UAE filters            │
  └─────────────────────┴──────────────────────────────────────────────┘
""")
print("  If region selector is MISSING on any page, the root cause is one of:")
print("  A) ui_styles.py has old thread-ID dedup (v4c) → selector vanishes after run 1")
print("  B) render_region_badge() not called before UAE renderer on that page")
print("  C) DuplicateWidgetID: tc_region_selector used in both ui_styles and UAE renderer")
print("  D) ui_styles.py ImportError → _render_rb = None → badge call silently skipped")
print()

# ─────────────────────────────────────────────────────────────
# 5. Summary & recommended action
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP2}")
print("  [5] SUMMARY & RECOMMENDED ACTION")
print(SEP2)

issues = []
if not version_ok:
    issues.append(f"ui_styles.py: version is '{found_version}', need v4d — run UPDATE_BADGE_SELECTBOX_V4d.py")
if has_thread_dedup:
    issues.append("ui_styles.py: OLD thread-ID dedup present — region selector vanishes on every re-run")
if not has_sidebar_sel:
    issues.append("ui_styles.py: no sidebar selectbox in render_region_badge — selector will never show")

for pname, res in page_results.items():
    if not res.get("ok"):
        issues.append(f"Page '{pname}': bootstrap issues detected — see details above")

if not issues:
    print("\n  ✅ All checks passed — region selector should be consistent on all pages.")
    print("  If it still vanishes in the browser, try:")
    print("    1. Hard-refresh (Ctrl+Shift+R)")
    print("    2. Clear browser cookies/session")
    print("    3. Check Streamlit logs for DuplicateWidgetID warnings")
    print("       tail -50 /tmp/streamlit.log | grep -i 'duplicate\\|widget\\|error'")
else:
    print(f"\n  ❌ {len(issues)} issue(s) found:\n")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    print("\n  RECOMMENDED FIXES:")
    if any("v4d" in i or "thread" in i for i in issues):
        print("  → Run: python3 UPDATE_BADGE_SELECTBOX_V4d.py")
    if any("bootstrap" in i for i in issues):
        print("  → Run: python3 DIAGNOSE_AND_FIX_PERMANENT.py")
    print("  → After fix: pkill -f 'streamlit run' && nohup venv/bin/streamlit run app.py \\")
    print("      --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &")

print(f"\n{SEP2}\n")
