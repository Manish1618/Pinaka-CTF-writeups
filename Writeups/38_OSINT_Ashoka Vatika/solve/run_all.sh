#!/usr/bin/env bash
# Usage: ./run_all.sh /path/to/05-Ashokavana
set -euo pipefail
F="${1:-05-Ashokavana}"
cd "$(dirname "$0")"
python3 stage1_decode.py "$F"
python3 stage2_garden.py "$F"
python3 stage3_bundle.py "$F" ba_result.pkl
python3 stage4_payload.py "$F" ba_result.pkl submission.json
python3 stage5_compare.py submission.json accepted_payload.json
