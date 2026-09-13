"""
Generate 5 sample lab-report PDFs with different clinical patterns
for testing/demoing the Report Translator.

Run:  python make_samples.py
"""

from fpdf import FPDF

REPORTS = {
    "report_1_all_normal": {
        "title": "CITY CARE DIAGNOSTICS — Annual Health Check (ALL NORMAL)",
        "lines": [
            "Hemoglobin 14.8 g/dL (Ref: 13.0 - 17.0)",
            "Total Leucocyte Count 7800 cells/uL (Ref: 4000 - 11000)",
            "Platelet Count 290000 cells/uL (Ref: 150000 - 410000)",
            "Fasting Blood Sugar 88 mg/dL (Ref: 70 - 99)",
            "HbA1c 5.2 % (Ref: 4.0 - 5.6)",
            "Total Cholesterol 168 mg/dL (Ref: < 200)",
            "Triglycerides 112 mg/dL (Ref: < 150)",
            "TSH 2.1 uIU/mL (Ref: 0.4 - 4.0)",
            "Vitamin D (25-OH) 46 ng/mL (Ref: 30 - 100)",
            "Vitamin B12 520 pg/mL (Ref: 200 - 900)",
        ],
    },
    "report_2_diabetes_pattern": {
        "title": "CITY CARE DIAGNOSTICS — Diabetic Follow-up Panel",
        "lines": [
            "Hemoglobin 13.6 g/dL (Ref: 13.0 - 17.0)",
            "Fasting Blood Sugar 187 mg/dL (Ref: 70 - 99)",
            "HbA1c 9.4 % (Ref: 4.0 - 5.6)",
            "Total Cholesterol 218 mg/dL (Ref: < 200)",
            "Triglycerides 265 mg/dL (Ref: < 150)",
            "Serum Creatinine 1.4 mg/dL (Ref: 0.6 - 1.3)",
            "Blood Urea 44 mg/dL (Ref: 15 - 40)",
        ],
    },
    "report_3_anemia_pattern": {
        "title": "CITY CARE DIAGNOSTICS — Fatigue Work-up Panel",
        "lines": [
            "Hemoglobin 8.9 g/dL (Ref: 13.0 - 17.0)",
            "Total Leucocyte Count 6200 cells/uL (Ref: 4000 - 11000)",
            "Platelet Count 310000 cells/uL (Ref: 150000 - 410000)",
            "Vitamin B12 145 pg/mL (Ref: 200 - 900)",
            "Vitamin D (25-OH) 16 ng/mL (Ref: 30 - 100)",
            "TSH 3.4 uIU/mL (Ref: 0.4 - 4.0)",
            "Fasting Blood Sugar 92 mg/dL (Ref: 70 - 99)",
        ],
    },
    "report_4_infection_pattern": {
        "title": "CITY CARE DIAGNOSTICS — Fever Panel",
        "lines": [
            "Hemoglobin 12.4 g/dL (Ref: 13.0 - 17.0)",
            "Total Leucocyte Count 16800 cells/uL (Ref: 4000 - 11000)",
            "Platelet Count 445000 cells/uL (Ref: 150000 - 410000)",
            "Blood Urea 36 mg/dL (Ref: 15 - 40)",
            "Serum Creatinine 1.1 mg/dL (Ref: 0.6 - 1.3)",
            "Fasting Blood Sugar 104 mg/dL (Ref: 70 - 99)",
        ],
    },
    "report_5_thyroid_cholesterol": {
        "title": "CITY CARE DIAGNOSTICS — Thyroid & Lipid Profile",
        "lines": [
            "TSH 11.2 uIU/mL (Ref: 0.4 - 4.0)",
            "Total Cholesterol 276 mg/dL (Ref: < 200)",
            "Triglycerides 198 mg/dL (Ref: < 150)",
            "Hemoglobin 12.8 g/dL (Ref: 13.0 - 17.0)",
            "Fasting Blood Sugar 96 mg/dL (Ref: 70 - 99)",
            "Vitamin D (25-OH) 22 ng/mL (Ref: 30 - 100)",
        ],
    },
}


def _latin(text: str) -> str:
    """Core PDF fonts are latin-1 only — replace unsupported chars."""
    return text.encode("latin-1", "replace").decode("latin-1")


def make_pdf(path: str, title: str, lines: list[str]) -> None:
    title, lines = _latin(title), [_latin(x) for x in lines]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.cell(0, 8, "CITY CARE DIAGNOSTICS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "Patient: Demo Patient  |  Report Date: 13 Sep 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.cell(0, 6, "----------------------------------", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 6, "LAB RESULTS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 6, "----------------------------------", new_x="LMARGIN", new_y="NEXT")
    for line in lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", style="I", size=10)
    pdf.cell(0, 6, "Interpretation: Values outside reference range need clinical correlation.", new_x="LMARGIN", new_y="NEXT")
    pdf.output(path)


for name, spec in REPORTS.items():
    make_pdf(f"{name}.pdf", spec["title"], spec["lines"])
    print("created", name + ".pdf")
