#!/usr/bin/env python3
"""
hotfix.py  ─  fixes the two visible problems from the screenshot
────────────────────────────────────────────────────────────────────────
PROBLEM 1  │ "UAEConnector not available." errors, all KPIs show 0
ROOT CAUSE │ uae_page_renderer._q() routed through UAEConnector which
           │ couldn't be imported; the try/except silently set it None
FIX        │ _q() now calls _direct_q() (direct psycopg2, no connector)
           │ _conn() function removed entirely

PROBLEM 2  │ Sidebar navigation items (State Dashboard / Analytics /
           │ UAE Dashboard) repeat 4-5 times down the sidebar
ROOT CAUSE │ app.py still lists pages/5_🇦🇪_UAE_Dashboard.py in
           │ st.navigation(). That page runs _render_rb() which writes
           │ sidebar nav links each time Streamlit inspects the page.
FIX        │ Remove the UAE st.Page() line from app.py (same as
           │ surgical_patch.py Step 1 – re-applied here to confirm)

INDIA SAFETY │ Zero changes to any India file. Only app.py line 10
             │ and utils/uae_page_renderer.py are touched.
────────────────────────────────────────────────────────────────────────
Run:
    cd ~/tutorcloud/tutorcloud-global-dashboard
    python3 hotfix.py
"""

import ast, shutil, pathlib, tokenize, io, sys
from datetime import datetime

ROOT = pathlib.Path(".")
TS   = datetime.now().strftime("%Y%m%d_%H%M%S")
CHANGED = []

def bak(p):
    b = pathlib.Path(f"{p}.bak.{TS}")
    shutil.copy2(p, b)
    print(f"    Backup → {b.name}")

def validate(src, label):
    try:
        list(tokenize.generate_tokens(io.StringIO(src).readline))
        ast.parse(src)
    except Exception as e:
        print(f"\n  ✗  Validation FAILED for {label}: {e}")
        sys.exit(1)

def write(p, old, new, label):
    if new == old:
        print(f"    ─  No change needed ({label})")
        return
    validate(new, label)
    bak(p)
    p.write_text(new, "utf-8")
    CHANGED.append(label)
    print(f"    ✓  Written: {p}")


# ═══════════════════════════════════════════════════════════════════════
# FIX 1  ─  uae_page_renderer.py  (UAEConnector → direct psycopg2)
# ═══════════════════════════════════════════════════════════════════════
print("\n[FIX 1] Removing UAEConnector dependency from uae_page_renderer.py ...")

rp = ROOT / "utils" / "uae_page_renderer.py"
if not rp.exists():
    print("  ✗  utils/uae_page_renderer.py not found – copy it first"); sys.exit(1)

src = rp.read_text("utf-8")

OLD_BLOCK = '''\
def _conn():
    """Return UAEConnector instance (cached in session state)."""
    if "uae_conn" not in st.session_state:
        if UAEConnector is None:
            st.error("UAEConnector not available.")
            return None
        st.session_state["uae_conn"] = UAEConnector()
    return st.session_state["uae_conn"]


def _q(sql: str, params=None) -> pd.DataFrame:
    """Run an ad-hoc query through the connector's internal _query method."""
    c = _conn()
    if c is None:
        return pd.DataFrame()
    try:
        if hasattr(c, "_query"):
            return c._query(sql, params or [])
        # fallback: direct psycopg2
        import psycopg2, psycopg2.extras
        with psycopg2.connect(
            host="localhost", dbname="tutorcloud_db",
            user="tutorcloud_admin", password="TutorCloud2024!Secure"
        ) as conn:
            return pd.read_sql_query(sql, conn, params=params or [])
    except Exception as e:
        st.warning(f"Query error: {e}")
        return pd.DataFrame()'''

NEW_BLOCK = '''\
def _q(sql: str, params=None) -> pd.DataFrame:
    """Direct psycopg2 query \u2013 no UAEConnector dependency."""
    return _direct_q(sql, params)'''

if OLD_BLOCK in src:
    new_src = src.replace(OLD_BLOCK, NEW_BLOCK, 1)
    print("    Replaced _conn() + old _q()  \u2192  lean _q() via _direct_q()")
    write(rp, src, new_src, "uae_page_renderer.py")
elif 'st.error("UAEConnector not available.")' in src:
    print("  ✗  Old block structure differs – trying line-level replacement ...")
    # Find and replace just the _conn function and rewrite _q
    import re
    new_src = re.sub(
        r'def _conn\(\):.*?(?=\ndef )',
        '', src, flags=re.DOTALL
    )
    new_src = re.sub(
        r'def _q\(sql.*?(?=\ndef |\Z)',
        'def _q(sql: str, params=None) -> pd.DataFrame:\n'
        '    """Direct psycopg2 query \u2013 no UAEConnector dependency."""\n'
        '    return _direct_q(sql, params)\n\n',
        new_src, flags=re.DOTALL
    )
    write(rp, src, new_src, "uae_page_renderer.py (regex fallback)")
elif "def _q(" in src and "_direct_q" in src and "_conn" not in src:
    print("    \u2713  Already fixed \u2013 _q() already uses _direct_q()")
else:
    print("  \u26a0  Pattern not matched. Check manually.")


# ═══════════════════════════════════════════════════════════════════════
# FIX 2  ─  app.py  (remove UAE page from st.navigation)
# ═══════════════════════════════════════════════════════════════════════
print("\n[FIX 2] Removing UAE page from app.py navigation ...")

ap = ROOT / "app.py"
if not ap.exists():
    print("  ✗  app.py not found"); sys.exit(1)

src = ap.read_text("utf-8")
lines_in  = src.splitlines(keepends=True)
lines_out = []
removed   = 0

for ln in lines_in:
    is_uae_page = (
        "st.Page(" in ln and
        "\U0001f1e6\U0001f1ea_UAE_Dashboard.py" in ln
    )
    if is_uae_page:
        print(f"    Removing: {ln.rstrip()}")
        removed += 1
    else:
        lines_out.append(ln)

if removed == 0:
    if "\U0001f1e6\U0001f1ea_UAE_Dashboard.py" not in src:
        print("    \u2713  UAE page already absent from app.py")
    else:
        print("  \u26a0  UAE page still present but line pattern didn't match")
        print("     Printing all st.Page lines for manual check:")
        for i, l in enumerate(lines_in, 1):
            if "st.Page(" in l:
                print(f"     L{i}: {l.rstrip()}")
else:
    write(ap, src, "".join(lines_out), "app.py")


# ═══════════════════════════════════════════════════════════════════════
# Summary + restart instructions
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print(f"  Files changed: {len(CHANGED)}")
for f in CHANGED: print(f"    \u2713  {f}")
print("="*60)
print("""
Restart Streamlit now:

  kill $(pgrep -f "streamlit run app.py"); sleep 3
  nohup venv/bin/streamlit run app.py \\
    --server.port 8501 --server.address 0.0.0.0 \\
    > logs/streamlit.log 2>&1 &
  echo "PID: $!"; sleep 5
  grep -i "error\\|traceback" logs/streamlit.log | head -5 \\
      || echo "No startup errors"
  tail -6 logs/streamlit.log
""")
