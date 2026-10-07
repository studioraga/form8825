from __future__ import annotations

import json
from pathlib import Path

from api.main import app

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "docs" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(out)
