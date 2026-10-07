#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

./scripts/verify_backend.sh
./scripts/verify_api_db.sh
./scripts/verify_frontend.sh

echo "============================================================"
echo "ALL FORM 8825 TASK 1-4 VALIDATION PASSED"
echo "============================================================"
