from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FormProfile:
    profile_id: str
    revision: str
    description: str
    line_base: dict[str, int]
    canonical_prefix: str = "property."


FORM_8825_2025_12 = FormProfile(
    profile_id="irs-8825-2025-12",
    revision="2025-12",
    description="IRS Form 8825 Rev. December 2025",
    line_base={
        "2a": 23,
        "2b": 27,
        "2c": 31,
        "3": 35,
        "4": 39,
        "5": 43,
        "6": 47,
        "7": 51,
        "8": 55,
        "9": 59,
        "10": 63,
        "11": 67,
        "12": 71,
        "13": 75,
        "14": 79,
        "15": 83,
        "16": 87,
        "17": 91,
        "18": 95,
        "19": 99,
    },
)

SYNTHETIC_2025_12 = FormProfile(
    profile_id="synthetic-8825-2025-12",
    revision="2025-12",
    description="Generated Form 8825 A/B/C fixture",
    line_base=FORM_8825_2025_12.line_base,
)

PROFILES = {
    FORM_8825_2025_12.profile_id: FORM_8825_2025_12,
    SYNTHETIC_2025_12.profile_id: SYNTHETIC_2025_12,
}


def detect_profile(fields: dict[str, Any]) -> FormProfile | None:
    """Identify a supported Form 8825 layout from field signatures.

    The detector intentionally relies on structural field signatures rather
    than filename. New IRS revisions should be added as explicit profiles with
    their own regression fixtures before being accepted.
    """
    keys = tuple(fields)
    if any(key.startswith("property.") for key in keys):
        return SYNTHETIC_2025_12
    if any(".Line2a[" in key for key in keys) and any("Table_Line1" in key for key in keys):
        return FORM_8825_2025_12
    return None
