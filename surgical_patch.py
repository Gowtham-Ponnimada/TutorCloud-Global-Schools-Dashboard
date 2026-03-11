#!/usr/bin/env python3
"""
surgical_patch.py
═══════════════════════════════════════════════════════════════════════
SURGICAL UAE INTEGRATION PATCH  –  based on confirmed diagnostic output
───────────────────────────────────────────────────────────────────────
EXACTLY 2 changes per page file  (confirmed from live diagnostic):

  app.py       → remove the UAE st.Page() line (L10)
  1_Home.py    → L64: replace st.switch_page(UAE) → render_uae_home()
  2_State.py   → L186: replace st.switch_page(UAE) → render_uae_state_dashboard()
  4_Analytics  → L61:  replace st.switch_page(UAE) → render_uae_analytics()

  Each page also gets ONE import line inserted after the last top-level
  import (before _current_region = ...).

INDIA CODE IS NOT TOUCHED:
  • No regex over India logic
  • st.stop() on the line after switch_page already exists — NOT duplicated
  • elif _current_region != "India" block untouched
  • All India rendering code below the if/elif block untouched

Run:
    cd ~/tutorcloud/tutorcloud-global-dashboard
    python3 surgical_patch.py
═══════════════════════════════════════════════════════════════════════
"""

import ast, shutil, pathlib, tokenize, io, sys
from datetime import datetime

ROOT = pathlib.Path(".")
TS   = datetime.now().strftime("%Y%m%d_%H%M%S")

# ── The ONE switch_page string that exists in all three page files ────────────
UAE_SWITCH = '    st.switch_page("pages/5_\U0001f1e6\U0001f1ea_UAE_Dashboard.py")'

# ── The ONE import region line that is identical in all three page files ──────
REGION_LINE = '_current_region = st.session_state.get("selected_region", "India")'

# ── The UAE st.Page() line to remove from app.py ─────────────────────────────
UAE_PAGE_LINE = '    st.Page("pages/5_\U0001f1e6\U0001f1ea_UAE_Dashboard.py",  title="\U0001f1e6\U0001f1ea UAE Dashboard"),'

CHANGED = []
ERRORS  = []

# ─────────────────────────────────────────────────────────────────────────────
def backup(p: pathlib.Path):
    bak = pathlib.Path(f"{p}.bak.{TS}")
    shutil.copy2(p, bak)
    print(f"    Backup  → {bak.name}")


def validate(src: str, label: str):
    """Tokenize + AST check. Abort on failure."""
    try:
        list(tokenize.generate_tokens(io.StringIO(src).readline))
        ast.parse(src)
    except Exception as e:
        print(f"\n  ✗  VALIDATION FAILED for {label}: {e}")
        print("     File NOT written. Original is untouched.")
        sys.exit(1)


def apply(p: pathlib.Path, old_src: str, new_src: str, label: str):
    """Validate new source, backup original, write new source."""
    if new_src == old_src:
        print(f"    ─  No change needed in {label}")
        return
    validate(new_src, label)
    backup(p)
    p.write_text(new_src, encoding="utf-8")
    CHANGED.append(label)
    print(f"    ✓  Written: {p}")


def find_page(pattern: str) -> pathlib.Path | None:
    hits = sorted((ROOT / "pages").glob(pattern))
    return hits[0] if hits else None


def insert_import_before_region(src: str, import_line: str) -> str:
    """
    Insert `import_line` immediately before the REGION_LINE.
    If import already present, skip.
    """
    if import_line.strip() in src:
        return src          # already imported
    lines = src.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip() == REGION_LINE:
            lines.insert(i, import_line + "\n")
            return "".join(lines)
    # Fallback: prepend at top
    return import_line + "\n" + src


# ═════════════════════════════════════════════════════════════════════════════
# STEP 0 – Verify uae_page_renderer.py is installed
# ═════════════════════════════════════════════════════════════════════════════
renderer = ROOT / "utils" / "uae_page_renderer.py"
print("\n[0] Checking utils/uae_page_renderer.py ...")
if not renderer.exists():
    print("  ✗  utils/uae_page_renderer.py NOT FOUND.")
    print("     Copy it from the package first:")
    print("     cp /tmp/uae_patch/utils/uae_page_renderer.py utils/")
    sys.exit(1)
try:
    ast.parse(renderer.read_text(encoding="utf-8"))
    print("  ✓  Renderer present and AST-valid")
except SyntaxError as e:
    print(f"  ✗  Renderer has SyntaxError: {e}")
    sys.exit(1)


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 – app.py  →  remove UAE st.Page() entry
# ═════════════════════════════════════════════════════════════════════════════
print("\n[1] Patching app.py  (remove UAE navigation entry) ...")
app_path = ROOT / "app.py"
if not app_path.exists():
    ERRORS.append("app.py not found")
else:
    old = app_path.read_text(encoding="utf-8")
    lines = old.splitlines(keepends=True)

    # Find and remove the exact UAE page line
    new_lines = []
    removed = 0
    for ln in lines:
        # Match the UAE st.Page line regardless of minor whitespace variation
        stripped = ln.strip()
        if (stripped.startswith('st.Page(') and
            '\U0001f1e6\U0001f1ea_UAE_Dashboard.py' in ln):
            print(f"    Removing: {ln.rstrip()}")
            removed += 1
        else:
            new_lines.append(ln)

    if removed == 0:
        # Already removed or different format — check if UAE is still in nav
        if '\U0001f1e6\U0001f1ea_UAE_Dashboard.py' in old:
            ERRORS.append("UAE page line found in app.py but pattern didn't match — check manually")
        else:
            print("    ─  UAE page already absent from app.py")
    else:
        new = "".join(new_lines)
        apply(app_path, old, new, "app.py")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 – pages/1_*Home.py  →  render_uae_home()
# ═════════════════════════════════════════════════════════════════════════════
print("\n[2] Patching Home page ...")
home = find_page("1_*Home*") or find_page("1_*home*")
if not home:
    ERRORS.append("Home page not found")
else:
    old = home.read_text(encoding="utf-8")

    # Verify the exact switch_page line is present
    if UAE_SWITCH not in old:
        if "render_uae_home" in old:
            print("    ─  Already patched (render_uae_home found)")
        else:
            ERRORS.append(f"{home.name}: switch_page UAE line not found — check L64 manually")
    else:
        # Change 1: replace switch_page with render call (st.stop() on next line stays)
        new = old.replace(UAE_SWITCH, "    render_uae_home()", 1)

        # Change 2: insert import before _current_region line
        new = insert_import_before_region(
            new, "from utils.uae_page_renderer import render_uae_home"
        )

        # Show exactly what changed
        for i, (ol, nl) in enumerate(
            zip(old.splitlines(), new.splitlines()), 1
        ):
            if ol != nl:
                print(f"    L{i:>4} BEFORE: {ol.rstrip()}")
                print(f"    L{i:>4} AFTER : {nl.rstrip()}")

        apply(home, old, new, home.name)


# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 – pages/2_*State_Dashboard.py  →  render_uae_state_dashboard()
# ═════════════════════════════════════════════════════════════════════════════
print("\n[3] Patching State Dashboard page ...")
state = find_page("2_*State*") or find_page("2_*state*")
if not state:
    ERRORS.append("State Dashboard page not found")
else:
    old = state.read_text(encoding="utf-8")

    if UAE_SWITCH not in old:
        if "render_uae_state_dashboard" in old:
            print("    ─  Already patched (render_uae_state_dashboard found)")
        else:
            ERRORS.append(f"{state.name}: switch_page UAE line not found — check L186 manually")
    else:
        new = old.replace(UAE_SWITCH, "    render_uae_state_dashboard()", 1)
        new = insert_import_before_region(
            new, "from utils.uae_page_renderer import render_uae_state_dashboard"
        )

        for i, (ol, nl) in enumerate(
            zip(old.splitlines(), new.splitlines()), 1
        ):
            if ol != nl:
                print(f"    L{i:>4} BEFORE: {ol.rstrip()}")
                print(f"    L{i:>4} AFTER : {nl.rstrip()}")

        apply(state, old, new, state.name)


# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 – pages/4_*Analytics.py  →  render_uae_analytics()
# ═════════════════════════════════════════════════════════════════════════════
print("\n[4] Patching Analytics page ...")
analytics = find_page("4_*Analytics*") or find_page("4_*analytics*")
if not analytics:
    ERRORS.append("Analytics page not found")
else:
    old = analytics.read_text(encoding="utf-8")

    if UAE_SWITCH not in old:
        if "render_uae_analytics" in old:
            print("    ─  Already patched (render_uae_analytics found)")
        else:
            ERRORS.append(f"{analytics.name}: switch_page UAE line not found — check L61 manually")
    else:
        new = old.replace(UAE_SWITCH, "    render_uae_analytics()", 1)
        new = insert_import_before_region(
            new, "from utils.uae_page_renderer import render_uae_analytics"
        )

        for i, (ol, nl) in enumerate(
            zip(old.splitlines(), new.splitlines()), 1
        ):
            if ol != nl:
                print(f"    L{i:>4} BEFORE: {ol.rstrip()}")
                print(f"    L{i:>4} AFTER : {nl.rstrip()}")

        apply(analytics, old, new, analytics.name)


# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 – Final India safety verification
# ═════════════════════════════════════════════════════════════════════════════
print("\n[5] India safety verification ...")
india_checks = [
    (find_page("1_*Home*"),     "render_uae_home",             "Home"),
    (find_page("2_*State*"),    "render_uae_state_dashboard",  "State Dashboard"),
    (find_page("4_*Analytics*"),"render_uae_analytics",        "Analytics"),
]
for page_path, render_fn, label in india_checks:
    if not page_path or not page_path.exists():
        continue
    src = page_path.read_text(encoding="utf-8")

    # 1. UAE render is guarded by if _current_region == "UAE"
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if render_fn + "()" in line:
            above = lines[i-1].strip() if i > 0 else ""
            below = lines[i+1].strip() if i+1 < len(lines) else ""
            guard_ok = '_current_region == "UAE"' in above
            stop_ok  = "st.stop()" in below or "st.stop()" in line
            print(f"    [{label}] render call at L{i+1}  "
                  f"| guarded by UAE check: {'✓' if guard_ok else '✗'}  "
                  f"| st.stop() present: {'✓' if stop_ok else '✗'}")

    # 2. India code still present
    india_keywords = ["India", "selected_state", "state_data",
                      "india", "district", "block"]
    found_india = [kw for kw in india_keywords if kw in src]
    print(f"    [{label}] India keywords still present: {found_india[:4]} ✓")

    # 3. switch_page UAE is gone
    if UAE_SWITCH in src:
        print(f"    [{label}] ✗  switch_page UAE still present — patch may have failed")
    else:
        print(f"    [{label}] st.switch_page(UAE) removed ✓")

    # 4. AST clean
    try:
        ast.parse(src)
        print(f"    [{label}] AST valid ✓")
    except SyntaxError as e:
        print(f"    [{label}] ✗  SyntaxError: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print(f"  Files patched : {len(CHANGED)}")
for f in CHANGED:
    print(f"    ✓  {f}")
if ERRORS:
    print(f"\n  Errors/warnings ({len(ERRORS)}):")
    for e in ERRORS:
        print(f"    ✗  {e}")
print("═"*60)

if not ERRORS:
    print("""
Next step — restart Streamlit:

  kill $(pgrep -f "streamlit run app.py"); sleep 3
  nohup venv/bin/streamlit run app.py \\
      --server.port 8501 --server.address 0.0.0.0 \\
      > logs/streamlit.log 2>&1 &
  echo "PID: $!"; sleep 5
  grep -i "error\\|traceback" logs/streamlit.log | head -5 \\
      || echo "No errors in startup log"
  tail -8 logs/streamlit.log
""")
else:
    print("\n  Fix errors above before restarting Streamlit.\n")
