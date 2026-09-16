"""Explicit synthetic expectations. These are not patient data or clinical ranges."""

from app.schemas.extraction import ExtractedPage, Span

# label, raw value, unit, raw reference, expected kind, exact decimal
ROWS: list[tuple[str, str, str, str, str, str | None]] = [
    ("Hemoglobin", "13.20", "g/dL", "12–15", "numeric", "13.20"),
    ("Vitamin D", "18", "ng/mL", "30–100", "numeric", "18"),
    ("TSH", "2.4", "mIU/L", "0.4–4.0", "numeric", "2.4"),
    ("Glucose", "<70", "mg/dL", "<100", "numeric", "70"),
    ("CRP", ">10", "mg/L", "Up to 5", "numeric", "10"),
    ("COVID test", "Negative", "", "Negative", "qualitative", None),
    ("Protein", "Trace", "", "", "qualitative", None),
    ("Titre", "1:80", "", "", "titre", None),
    ("Unknown test", "5", "xyz", "", "numeric", "5"),
    ("No reference", "1", "mg/dL", "", "numeric", "1"),
    ("No unit", "2", "", "1-3", "numeric", "2"),
    ("हिंदी परीक्षण", "13.2", "g/dL", "12—15", "numeric", "13.2"),
    ("Ambiguous zero", "O.5", "mg/L", "", "unparsed", None),
    ("Ambiguous one", "l.5", "mg/L", "", "unparsed", None),
    ("Decimal", "0.0050", "%", "0.001–0.010", "numeric", "0.0050"),
    ("Negative number", "−2.50", "mmol/L", "−3–−1", "numeric", "-2.50"),
    ("Less than", "<5", "mg/L", "", "numeric", "5"),
    ("Greater than", ">200", "mg/L", "", "numeric", "200"),
    ("Inclusive", "≤5", "mg/L", "≤10", "numeric", "5"),
    ("Inclusive high", ">=40", "mg/L", ">40", "numeric", "40"),
    ("Interval", "5–10", "", "", "interval", None),
    ("Ordinal", "3+", "", "", "ordinal", None),
    ("Antibody", "Reactive", "", "", "qualitative", None),
    ("Pathogen", "Not detected", "", "", "qualitative", None),
    ("Superscript", "5", "10³/uL", "", "numeric", "5"),
    ("Caret unit", "5", "10^3/uL", "", "numeric", "5"),
    ("Context range", "5", "mg/L", "Male: 3–7; Female: 2–6", "numeric", "5"),
    ("Age range", "5", "mg/L", "Age 5–10: 2–6", "numeric", "5"),
    ("Missing", "", "mg/L", "1–3", "missing", None),
    ("Comma decimal", "1,20", "mg/L", "", "unparsed", None),
    ("Zero", "0", "%", "", "numeric", "0"),
    ("One", "1", "%", "", "numeric", "1"),
]
NATIVE_LINES = [
    "SYNTHETIC TABLE - NOT A PATIENT REPORT",
    "Parameter Result Unit Reference",
    "Hemoglobin 13.20 g/dL 12-15",
    "Vitamin D 18 ng/mL 30-100",
    "TSH 2.4 mIU/L 0.4-4.0",
    "Glucose <70 mg/dL <100",
    "CRP >10 mg/L Up to 5",
]


def page(text: str, number: int = 1) -> ExtractedPage:
    return ExtractedPage(
        page_number=number,
        text=text,
        method="native_text",
        width=600,
        height=800,
        coordinate_system="pdf_points_bottom_left",
        warnings=[],
        spans=[Span(text=line, bbox=(10, 10, 500, 20)) for line in text.splitlines()],
    )


def dataset() -> list[ExtractedPage]:
    return [
        page(
            "Parameter | Result | Unit | Reference\n"
            + "\n".join(" | ".join(row[:4]) for row in ROWS[:16])
        ),
        page(
            "Parameter | Result | Unit | Reference\n"
            + "\n".join(" | ".join(row[:4]) for row in ROWS[16:]),
            2,
        ),
    ]
