#!/usr/bin/env python3
"""
uae_mv_gender_fix_v4.py
-----------------------
Fixes the gender substring bug in uae_curriculum_kpi_mv_v3.sql.

Root cause:
- LOWER(gender) LIKE '%male%' matches 'female'
- So male_students / male_teachers incorrectly include female counts

Fix:
- Replace substring LIKE logic with exact normalized matching:
    LOWER(BTRIM(COALESCE(gender,''))) IN ('male', 'بنين')
    LOWER(BTRIM(COALESCE(gender,''))) IN ('female', 'بنات')
"""

from pathlib import Path
from datetime import datetime
import shutil
import sys

SQL_FILE = Path("uae_curriculum_kpi_mv_v3.sql")

OLD_ENROLLMENT = """        SUM(CASE WHEN LOWER(gender) LIKE '%female%' OR LOWER(gender) LIKE '%بنات%'
                 THEN student_count ELSE 0 END)                        AS female_students,
        SUM(CASE WHEN LOWER(gender) LIKE '%male%'  OR LOWER(gender) LIKE '%بنين%'
                 THEN student_count ELSE 0 END)                        AS male_students,"""

NEW_ENROLLMENT = """        SUM(CASE
                WHEN LOWER(BTRIM(COALESCE(gender,''))) IN ('female', 'بنات')
                THEN student_count ELSE 0
            END)                                                       AS female_students,
        SUM(CASE
                WHEN LOWER(BTRIM(COALESCE(gender,''))) IN ('male', 'بنين')
                THEN student_count ELSE 0
            END)                                                       AS male_students,"""

OLD_TEACHER = """        SUM(CASE WHEN LOWER(gender) LIKE '%female%' OR LOWER(gender) LIKE '%بنات%'
                 THEN teacher_count ELSE 0 END)                        AS female_teachers,
        SUM(CASE WHEN LOWER(gender) LIKE '%male%'  OR LOWER(gender) LIKE '%بنين%'
                 THEN teacher_count ELSE 0 END)                        AS male_teachers,"""

NEW_TEACHER = """        SUM(CASE
                WHEN LOWER(BTRIM(COALESCE(gender,''))) IN ('female', 'بنات')
                THEN teacher_count ELSE 0
            END)                                                       AS female_teachers,
        SUM(CASE
                WHEN LOWER(BTRIM(COALESCE(gender,''))) IN ('male', 'بنين')
                THEN teacher_count ELSE 0
            END)                                                       AS male_teachers,"""

def main():
    print("\n" + "━" * 62)
    print("  UAE MV Gender Fix v4  (male/female exact-match correction)")
    print("━" * 62 + "\n")

    if not SQL_FILE.exists():
        print(f"❌ File not found: {SQL_FILE}")
        sys.exit(1)

    src = SQL_FILE.read_text(encoding="utf-8")

    if "MV_GENDER_FIX_v4" in src:
        print("⚠️ SQL file already patched with v4 marker. Nothing to do.")
        return

    changed = False

    if OLD_ENROLLMENT in src:
        src = src.replace(OLD_ENROLLMENT, NEW_ENROLLMENT + "\n        -- MV_GENDER_FIX_v4: exact gender match for enrollment", 1)
        print("✅ Enrollment gender logic patched.")
        changed = True
    else:
        print("❌ Enrollment gender block not found.")

    if OLD_TEACHER in src:
        src = src.replace(OLD_TEACHER, NEW_TEACHER + "\n        -- MV_GENDER_FIX_v4: exact gender match for teachers", 1)
        print("✅ Teacher gender logic patched.")
        changed = True
    else:
        print("❌ Teacher gender block not found.")

    if not changed:
        print("\n❌ No changes applied. SQL patterns not matched.")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = SQL_FILE.with_name(f"{SQL_FILE.name}.bak_v4_{ts}")
    shutil.copy2(SQL_FILE, backup)
    print(f"✅ Backup created: {backup.name}")

    SQL_FILE.write_text(src, encoding="utf-8")
    print(f"✅ Updated: {SQL_FILE.name}")

    checks = [
        "IN ('female', 'بنات')",
        "IN ('male', 'بنين')",
        "MV_GENDER_FIX_v4",
    ]
    missing = [c for c in checks if c not in src]

    if missing:
        print(f"❌ Verification failed. Missing markers: {missing}")
        sys.exit(1)

    print("\n✅ Patch applied successfully.")
    print("\nNext steps:")
    print("1. Rebuild the MV")
    print("2. Validate Pakistani curriculum totals")
    print("3. Restart Streamlit")
    print("4. Commit and push\n")


if __name__ == "__main__":
    main()
