from pathlib import Path
import re
import py_compile

path = Path("us_phase1_final_1a_load.py")
text = path.read_text(encoding="utf-8")

replacement = """        CASE
            WHEN c.virtual_text IS NULL OR BTRIM(c.virtual_text) = '' THEN 'Unknown'
            WHEN LOWER(BTRIM(c.virtual_text)) = 'no virtual instruction' THEN 'Brick & Mortar'
            WHEN LOWER(BTRIM(c.virtual_text)) = 'supplemental virtual' THEN 'Both'
            WHEN LOWER(BTRIM(c.virtual_text)) = 'exclusively virtual' THEN 'Virtual'
            WHEN LOWER(BTRIM(c.virtual_text)) = 'primarily virtual' THEN 'Virtual'
            WHEN LOWER(BTRIM(c.virtual_text)) IN ('missing', 'not reported') THEN 'Unknown'
            ELSE 'Unknown'
        END AS delivery_model,"""

pattern = re.compile(
    r"""        CASE\s*
            WHEN\s+c\.virtual_text\s+IS\s+NULL\s+OR\s+BTRIM\(c\.virtual_text\)\s*=\s*''\s+THEN\s+'Unknown'
            .*?
        END\s+AS\s+delivery_model,""",
    re.S | re.X,
)

new_text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f"Expected to replace 1 delivery_model CASE block, replaced {count}")

backup = Path("us_phase1_final_1a_load.py.bak_delivery_model_fix_v1")
backup.write_text(text, encoding="utf-8")
path.write_text(new_text, encoding="utf-8")

py_compile.compile(str(path), doraise=True)
print("Backup created:", backup)
print("Updated:", path)
