#!/usr/bin/env bash
# =============================================================
#  UAE SCHOOL DATA DOWNLOADER
#  Downloads CSVs/XLSX from 3 open-data sources:
#    1. KHDA Dubai Pulse  (direct CSV – no auth)
#    2. KHDA Website      (XLSX – direct link)
#    3. MOE Open Data     (manual + wget fallback)
#
#  Run from:  ~/tutorcloud/etl/
#  Usage:     bash 01_download_uae_data.sh
# =============================================================
set -euo pipefail

RAW_DIR="$HOME/tutorcloud/etl/data/raw/uae"
mkdir -p "$RAW_DIR"
LOG="$RAW_DIR/download.log"
echo "=== UAE Data Download $(date) ===" | tee "$LOG"

# -----------------------------------------------------------
# SOURCE 1: Dubai Pulse – KHDA Private Schools CSV (no auth)
# Fields: school_id, name_eng, lat, long, curriculum, rating,
#         area, student_count, established_on, contact info
# Updated: Feb 2026 | ~900 schools
# -----------------------------------------------------------
echo "[1/4] Downloading KHDA Dubai Pulse school_search.csv ..." | tee -a "$LOG"
wget -q --show-progress -O "$RAW_DIR/khda_dubai_private_schools.csv" \
  "https://www.dubaipulse.gov.ae/dataset/2ae67e78-833f-4638-9b6f-9f5a3f40ba44/resource/062647ff-ac22-4fe4-a1ab-cbbef6037c90/download/school_search.csv" \
  2>>"$LOG" && echo "  [OK] khda_dubai_private_schools.csv" | tee -a "$LOG" \
  || echo "  [WARN] Direct CSV failed – use XLSX fallback below" | tee -a "$LOG"

# -----------------------------------------------------------
# SOURCE 2: KHDA Website – Dubai Private Schools XLSX (1.4 MB)
# Richer dataset: fee ranges, gender, grade range, no. of teachers
# Updated: November 2025
# -----------------------------------------------------------
echo "[2/4] Downloading KHDA DubaiPrivateSchoolsOpenData.xlsx ..." | tee -a "$LOG"
wget -q --show-progress \
  --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120" \
  -O "$RAW_DIR/khda_dubai_schools_full.xlsx" \
  "https://web.khda.gov.ae/KHDA/media/KHDA/DubaiPrivateSchoolsOpenData.xlsx" \
  2>>"$LOG" && echo "  [OK] khda_dubai_schools_full.xlsx" | tee -a "$LOG" \
  || echo "  [WARN] XLSX download failed – download manually (see README)" | tee -a "$LOG"

# -----------------------------------------------------------
# SOURCE 3: Bayanat.ae – GE Public Schools 2018-2024 (CSV)
# Covers: ALL 7 emirates, public schools, enrollment, staff
# Portal: https://admin.bayanat.ae/Home/DatasetInfo?dID=...
# NOTE: These require clicking download on the portal.
# Script attempts wget; if blocked, prints manual instructions.
# -----------------------------------------------------------
echo "[3/4] Attempting Bayanat GE datasets (may require manual download) ..." | tee -a "$LOG"

BAYANAT_DATASETS=(
  "ge_public_schools_2018_2024|https://bayanat.ae/en/Datasets/Dataset-info?id=1dHDH5iN6ADu2-M-NAE0n8aY1PCoxgGM7hVVP6E86TI"
  "ge_private_schools_2018_2024|https://bayanat.ae/en/Datasets/Dataset-info?id=mseOQ0ClPRHvUOz1FHdKbG07ZL7QMuNRmUo3hx7u7yA"
  "ge_staff_2018_2024|https://bayanat.ae/en/Datasets/Dataset-info?id=y9nb6W-UIG-1PfWIa74vrDtI2ddh-iPRoc2yfGJhJSA"
)

for entry in "${BAYANAT_DATASETS[@]}"; do
  NAME="${entry%%|*}"
  URL="${entry##*|}"
  echo "  -> $NAME : visit $URL" | tee -a "$LOG"
  echo "     Save file as: $RAW_DIR/${NAME}.csv" | tee -a "$LOG"
done

# -----------------------------------------------------------
# SOURCE 4: MOE Open Data – Schools by Emirate + Curriculum
# Portal: https://www.moe.gov.ae/En/OpenData/pages/home.aspx
# Available as direct download links on the page (XLSX/CSV)
# -----------------------------------------------------------
echo "[4/4] MOE Open Data – manual download required ..." | tee -a "$LOG"
echo "  Visit: https://www.moe.gov.ae/En/OpenData/pages/home.aspx" | tee -a "$LOG"
echo "  Download: 'Number of Schools by Emirate, Curriculum, Gender' -> save as moe_schools_by_emirate.xlsx" | tee -a "$LOG"
echo "  Download: 'Student Enrollment by Level, Gender, Nationality' -> save as moe_enrollment.xlsx" | tee -a "$LOG"
echo "  Save files to: $RAW_DIR/" | tee -a "$LOG"

# -----------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------
echo "" | tee -a "$LOG"
echo "=== Download Summary ===" | tee -a "$LOG"
ls -lh "$RAW_DIR"/ 2>/dev/null | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo "Next step: bash 02_etl_uae_to_postgres.py" | tee -a "$LOG"
echo "=== Done ===" | tee -a "$LOG"
