from __future__ import annotations

from pathlib import Path

from pdf2image import convert_from_path
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "data" / "f8825_multi_ABC_flattened.pdf"
out = ROOT / "data" / "f8825_multi_ABC_scanned.pdf"

pages = convert_from_path(str(src), dpi=300, first_page=1, last_page=1)
if not pages:
    raise SystemExit("No rendered page")
image = pages[0].convert("RGB")

# Re-embed the raster page with ReportLab invariant mode so the image-only PDF
# is byte-reproducible and does not inherit timestamp metadata from PIL's PDF writer.
c = canvas.Canvas(str(out), pagesize=letter, invariant=1)
w, h = letter
c.drawImage(ImageReader(image), 0, 0, width=w, height=h, preserveAspectRatio=False, mask="auto")
c.showPage()
c.save()
print(out)
