#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

steps=(
  scripts/verify_p0_01_profiles.sh
  scripts/verify_p0_02_flattened.sh
  scripts/verify_p0_03_ocr.sh
  scripts/verify_p1_01_migrations.sh
  scripts/verify_p1_02_auth_rbac.sh
  scripts/verify_p1_03_concurrency.sh
  scripts/verify_p1_04_duplicates.sh
  scripts/verify_p1_05_audit_identity.sh
  scripts/verify_p2_01_background_jobs.sh
  scripts/verify_p2_02_observability.sh
)

for step in "${steps[@]}"; do
  echo "============================================================"
  echo "RUN: $step"
  "$step"
done

if [[ "${SKIP_FRONTEND:-0}" == "1" ]]; then
  echo "SKIP_FRONTEND=1: P2.3 React component/accessibility gate not executed"
else
  echo "============================================================"
  echo "RUN: scripts/verify_p2_03_frontend_accessibility.sh"
  scripts/verify_p2_03_frontend_accessibility.sh
fi

echo "============================================================"
echo "RUN: scripts/verify_p2_04_openapi_contract.sh"
scripts/verify_p2_04_openapi_contract.sh

echo "============================================================"
echo "ALL PRIORITY ENHANCEMENT GATES PASSED"
echo "============================================================"
