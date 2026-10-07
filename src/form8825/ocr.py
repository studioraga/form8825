from __future__ import annotations

from pathlib import Path
from typing import Any

from .flattened import SYNTHETIC_FLAT, FlatLayoutProfile


class OCRDependencyError(RuntimeError):
    pass


def _deps():
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from pytesseract import Output
    except Exception as exc:  # pragma: no cover - environment-specific
        raise OCRDependencyError(
            "OCR requires requirements-ocr.txt plus system Tesseract and Poppler utilities"
        ) from exc
    return convert_from_path, pytesseract, Output


def render_first_page(pdf_path: str | Path, dpi: int = 300):
    convert_from_path, _, _ = _deps()
    pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
    if not pages:
        raise OCRDependencyError("PDF rendering returned no pages")
    return pages[0]


def detect_ocr_profile(image) -> FlatLayoutProfile | None:
    _, pytesseract, _ = _deps()
    text = pytesseract.image_to_string(image, config="--psm 6")
    normalized = " ".join(text.lower().split())
    if "form 8825" in normalized and "simulated" in normalized:
        return SYNTHETIC_FLAT
    return None


def _ocr_tokens(image) -> list[dict[str, Any]]:
    _, pytesseract, Output = _deps()
    data = pytesseract.image_to_data(image, output_type=Output.DICT, config="--psm 6")
    out: list[dict[str, Any]] = []
    for i, text in enumerate(data["text"]):
        text = (text or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        out.append(
            {
                "text": text,
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
                "confidence": conf,
            }
        )
    return out


def _text_in_pdf_bbox(tokens, bbox, image_width: int, image_height: int, pdf_width=612.0, pdf_height=792.0):
    x0, top, x1, bottom = bbox
    px0, px1 = x0 / pdf_width * image_width, x1 / pdf_width * image_width
    py0, py1 = top / pdf_height * image_height, bottom / pdf_height * image_height
    selected = []
    for t in tokens:
        cx = t["left"] + t["width"] / 2
        cy = t["top"] + t["height"] / 2
        if px0 <= cx <= px1 and py0 <= cy <= py1 and t["confidence"] >= 20:
            selected.append(t)
    selected.sort(key=lambda t: (t["top"], t["left"]))
    return " ".join(t["text"] for t in selected)


def parse_scanned(pdf_path: str | Path, parse_money) -> list[dict[str, Any]]:
    from .extractor import EXPENSE_KEYS, INCOME_KEYS, PROPERTY_NAMES, TOTAL_KEYS, _empty_property

    image = render_first_page(pdf_path)
    profile = detect_ocr_profile(image)
    if profile is None:
        raise OCRDependencyError("No supported OCR layout profile recognized")
    tokens = _ocr_tokens(image)
    props = {p: _empty_property(p) for p in PROPERTY_NAMES}

    for p, bbox in profile.address_boxes.items():
        props[p]["property_address"] = _text_in_pdf_bbox(tokens, bbox, image.width, image.height)
    for line, boxes in profile.line_boxes.items():
        for p, bbox in boxes.items():
            raw = _text_in_pdf_bbox(tokens, bbox, image.width, image.height)
            if line in INCOME_KEYS:
                props[p]["income_line_items"][INCOME_KEYS[line]] = parse_money(raw)
            elif line in EXPENSE_KEYS:
                props[p]["expense_line_items"][EXPENSE_KEYS[line]] = parse_money(raw)
            elif line in TOTAL_KEYS:
                props[p]["totals"][TOTAL_KEYS[line]] = parse_money(raw)

    return [p for p in props.values() if p["property_address"] or any(p["totals"].values())]
