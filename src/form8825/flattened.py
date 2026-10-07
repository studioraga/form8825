from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber

from .profiles import FORM_8825_2025_12


@dataclass(frozen=True)
class FlatLayoutProfile:
    profile_id: str
    marker: str
    page: int
    page_height: float
    address_boxes: dict[str, tuple[float, float, float, float]]
    line_boxes: dict[str, dict[str, tuple[float, float, float, float]]]


def _bbox_from_reportlab(x: float, y: float, width: float, height: float, page_height: float = 792.0):
    # pdfplumber uses (x0, top, x1, bottom); ReportLab uses bottom-left origin.
    return (x, page_height - (y + height), x + width, page_height - y)


def synthetic_flat_profile() -> FlatLayoutProfile:
    cols = {"A": 300.0, "B": 410.0, "C": 510.0}
    address_y = 687.0
    rows = ["2a", "2b", "2c", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "17", "18", "19"]
    y = 660.0
    line_boxes: dict[str, dict[str, tuple[float, float, float, float]]] = {}
    for line in rows:
        line_boxes[line] = {
            p: _bbox_from_reportlab(x, y, 90.0, 12.0)
            for p, x in cols.items()
        }
        y -= 20.0
    return FlatLayoutProfile(
        profile_id="synthetic-8825-2025-12-flat",
        marker="FORM8825_FLAT_PROFILE=synthetic-8825-2025-12-flat",
        page=0,
        page_height=792.0,
        address_boxes={p: _bbox_from_reportlab(x, address_y, 90.0, 12.0) for p, x in cols.items()},
        line_boxes=line_boxes,
    )


SYNTHETIC_FLAT = synthetic_flat_profile()


def detect_flattened_profile(pdf_path: str | Path) -> FlatLayoutProfile | None:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return None
            text = pdf.pages[0].extract_text() or ""
    except Exception:
        return None
    if SYNTHETIC_FLAT.marker in text:
        return SYNTHETIC_FLAT
    return None


def _text_in_box(page, bbox: tuple[float, float, float, float]) -> str:
    text = page.crop(bbox).extract_text(x_tolerance=1, y_tolerance=2) or ""
    return " ".join(text.split())


def parse_flattened(pdf_path: str | Path, profile: FlatLayoutProfile, parse_money) -> list[dict[str, Any]]:
    from .extractor import EXPENSE_KEYS, INCOME_KEYS, PROPERTY_NAMES, TOTAL_KEYS, _empty_property

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[profile.page]
        props = {p: _empty_property(p) for p in PROPERTY_NAMES}
        for p, bbox in profile.address_boxes.items():
            props[p]["property_address"] = _text_in_box(page, bbox)
        for line, boxes in profile.line_boxes.items():
            for p, bbox in boxes.items():
                raw = _text_in_box(page, bbox)
                if line in INCOME_KEYS:
                    props[p]["income_line_items"][INCOME_KEYS[line]] = parse_money(raw)
                elif line in EXPENSE_KEYS:
                    props[p]["expense_line_items"][EXPENSE_KEYS[line]] = parse_money(raw)
                elif line in TOTAL_KEYS:
                    props[p]["totals"][TOTAL_KEYS[line]] = parse_money(raw)

    return [
        props[p]
        for p in PROPERTY_NAMES
        if props[p]["property_address"]
        or any(props[p]["income_line_items"].values())
        or any(props[p]["expense_line_items"].values())
        or any(props[p]["totals"].values())
    ]
