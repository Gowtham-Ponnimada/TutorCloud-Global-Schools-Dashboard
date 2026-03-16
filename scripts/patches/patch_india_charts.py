#!/usr/bin/env python3
"""
India Dashboard Chart Margin Fix
Fixes r=220 and r=350 right-margin cutoff on charts in India State Dashboard and Analytics.
Run from ~/tutorcloud/tutorcloud-global-dashboard/
"""
import os, ast, shutil, re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "india_state.py":     os.path.join(BASE_DIR, "india_state.py"),
    "india_analytics.py": os.path.join(BASE_DIR, "india_analytics.py"),
}

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
print("=== India Dashboard Chart Margin Fix ===\n")

all_ok = True
for fname, fpath in FILES.items():
    if not os.path.exists(fpath):
        print(f"  ❌ File not found: {fpath}")
        all_ok = False
        continue

    bak = fpath + f".bak_chart_margin_{ts}"
    shutil.copy2(fpath, bak)
    print(f"  📦 Backup: {bak}")

    text = open(fpath, "r", encoding="utf-8").read()
    original = text

    # Fix r=220 → r=40 in margin=dict(...)
    # Pattern: r=220 inside margin=dict(...)
    r220_count = text.count("r=220")
    r350_count = text.count("r=350")
    
    text = text.replace("r=220", "r=40")
    text = text.replace("r=350", "r=40")
    
    changes = r220_count + r350_count
    
    if changes == 0:
        print(f"  ⚠️  No r=220/r=350 found in {fname} — already patched?")
        continue
    
    open(fpath, "w", encoding="utf-8").write(text)
    
    try:
        ast.parse(text)
        print(f"  ✅ {fname} — Fixed {r220_count}x r=220 and {r350_count}x r=350 → r=40 | AST OK")
    except SyntaxError as e:
        print(f"  ❌ {fname} — Syntax error: {e}")
        shutil.copy2(bak, fpath)
        print(f"     ↩️  Rolled back")
        all_ok = False

print(f"\n{'✅ All files patched successfully' if all_ok else '❌ Some files failed'}")
print("\nNext steps:")
print("  1. Restart Streamlit")
print("  2. Test India State Dashboard → Grade Enrollment chart, District PTR chart, Block PTR chart")
print("  3. Test India Analytics → Geographic Maps chart")
print("  4. Git: git add india_state.py india_analytics.py && git commit -m 'fix: India - correct chart right-margin cutoff (r=220/r=350 → r=40)' && git push origin main")
