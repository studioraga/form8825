from __future__ import annotations
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

ROOT = Path(__file__).resolve().parents[1]
OUT_PDF = ROOT / "data" / "f8825_multi_ABC.pdf"
OUT_JSON = ROOT / "data" / "f8825_multi_ABC_expected.json"

source = [
    {
        "property_name": "A", "property_address": "101 Alpha Ave, Austin, TX 78701",
        "income_line_items": {"gross_rents": 120000, "other_income": 5000},
        "expense_line_items": {"advertising": 1200, "auto_travel": 900, "cleaning_maintenance": 8500, "commissions": 2500, "insurance": 6000, "interest": 18000, "legal_professional": 1500, "real_estate_taxes": 11000, "repairs": 7000, "utilities": 4200, "wages_salaries": 10000, "depreciation": 15000, "other_deductions": 3200},
    },
    {
        "property_name": "B", "property_address": "202 Beta Blvd, Denver, CO 80202",
        "income_line_items": {"gross_rents": 210000, "other_income": 2500},
        "expense_line_items": {"advertising": 1800, "auto_travel": 1200, "cleaning_maintenance": 13200, "commissions": 4000, "insurance": 9200, "interest": 31000, "legal_professional": 2400, "real_estate_taxes": 19600, "repairs": 11500, "utilities": 7200, "wages_salaries": 22000, "depreciation": 26000, "other_deductions": 5100},
    },
    {
        "property_name": "C", "property_address": "303 Gamma Rd, Seattle, WA 98101",
        "income_line_items": {"gross_rents": 175000, "other_income": 7500},
        "expense_line_items": {"advertising": 1500, "auto_travel": 1100, "cleaning_maintenance": 10400, "commissions": 3300, "insurance": 7800, "interest": 24000, "legal_professional": 1900, "real_estate_taxes": 15400, "repairs": 9200, "utilities": 6100, "wages_salaries": 16500, "depreciation": 21500, "other_deductions": 4200},
    },
]
for p in source:
    ti = sum(p["income_line_items"].values())
    te = sum(p["expense_line_items"].values())
    p["totals"] = {"total_rental_income": ti, "total_expenses": te, "net_income": ti-te}

c = canvas.Canvas(
    str(OUT_PDF),
    pagesize=letter,
    invariant=1,
)
w,h = letter
c.setTitle("Simulated Form 8825 - Properties A B C")
c.setFont("Helvetica-Bold", 14)
c.drawString(36, h-38, "Form 8825 - Simulated Multi-Property Test Fixture")
c.setFont("Helvetica", 8)
c.drawString(36, h-53, "PDF and expected JSON are generated from the same source data; not for filing.")

cols = {"label": 36, "A": 300, "B": 410, "C": 520}
for p in source:
    x = cols[p["property_name"]]
    c.setFont("Helvetica-Bold", 9); c.drawString(x, h-78, p["property_name"])
    c.setFont("Helvetica", 6); c.drawString(x, h-90, p["property_address"][:30])
    c.acroForm.textfield(name=f"property.{p['property_name']}.address", value=p["property_address"], x=x, y=h-105, width=105, height=12, borderWidth=0, fontSize=6)

rows = [
    ("2a", "Gross rents", "gross_rents", "income_line_items"),
    ("2b", "Other income", "other_income", "income_line_items"),
    ("2c", "Total rental income", "total_rental_income", "totals"),
    ("3", "Advertising", "advertising", "expense_line_items"),
    ("4", "Auto and travel", "auto_travel", "expense_line_items"),
    ("5", "Cleaning and maintenance", "cleaning_maintenance", "expense_line_items"),
    ("6", "Commissions", "commissions", "expense_line_items"),
    ("7", "Insurance", "insurance", "expense_line_items"),
    ("8", "Interest", "interest", "expense_line_items"),
    ("9", "Legal/professional", "legal_professional", "expense_line_items"),
    ("10", "Real estate taxes", "real_estate_taxes", "expense_line_items"),
    ("11", "Repairs", "repairs", "expense_line_items"),
    ("12", "Utilities", "utilities", "expense_line_items"),
    ("13", "Wages and salaries", "wages_salaries", "expense_line_items"),
    ("14", "Depreciation", "depreciation", "expense_line_items"),
    ("17", "Other deductions", "other_deductions", "expense_line_items"),
    ("18", "Total expenses", "total_expenses", "totals"),
    ("19", "Net income", "net_income", "totals"),
]
y = h-132
c.setFont("Helvetica", 7)
for line,label,key,bucket in rows:
    c.drawString(cols["label"], y+3, f"{line}  {label}")
    for p in source:
        x=cols[p["property_name"]]
        value=p[bucket][key]
        c.acroForm.textfield(name=f"property.{p['property_name']}.line{line}", value=f"{value:,}", x=x, y=y, width=90, height=12, borderWidth=1, fontSize=7)
    y -= 20

c.setFont("Helvetica-Bold", 8)
c.drawString(36, y-2, f"Grand total net income: {sum(p['totals']['net_income'] for p in source):,}")
c.save()
OUT_JSON.write_text(json.dumps(source, indent=2)+"\n", encoding="utf-8")
print(OUT_PDF)
print(OUT_JSON)
