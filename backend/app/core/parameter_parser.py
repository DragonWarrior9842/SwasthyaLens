"""Conservative table grammar. All offsets are Unicode codepoints, end exclusive."""

import json
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast

from app.schemas.extraction import ExtractedPage
from app.schemas.parameters import CandidateContent, ParameterFields, RawFields

EXTRACTOR_VERSION = "table-candidates-v1"
_config = json.loads(Path(__file__).with_name("parameter_aliases.json").read_text("utf-8"))
RULES_VERSION: str = _config["version"]
ALIASES: dict[str, str] = _config["aliases"]
NUMBER = r"[-−+]?(?:[0-9]{1,20}(?:\.[0-9]{1,12})?|\.[0-9]{1,12})"
NUMERIC = re.compile(rf"(?P<cmp><=|>=|[<>≤≥=])?\s*(?P<num>{NUMBER})")
RANGE = re.compile(rf"({NUMBER})\s*[-–—]\s*({NUMBER})")
QUALITATIVE = {
    "negative",
    "positive",
    "reactive",
    "non reactive",
    "non-reactive",
    "trace",
    "not detected",
    "detected",
}
FLAGS = {"H", "L", "High", "Low", "Abnormal"}
HEADERS = {
    "parameter": "label",
    "test": "label",
    "test name": "label",
    "sample label": "label",
    "investigation": "label",
    "result": "value",
    "value": "value",
    "unit": "unit",
    "units": "unit",
    "reference": "reference",
    "reference range": "reference",
    "flag": "flag",
}


class ParserLimit(Exception):
    pass


def key(value: str) -> str:
    return " ".join(value.casefold().split())


def decimal_text(value: str) -> str:
    # Decimal construction is exact; do not normalize away trailing zeros.
    return format(Decimal(value.replace("−", "-")), "f")


def fields(raw: RawFields, source_flag: str | None = None) -> ParameterFields:
    value = raw.raw_value
    result = ParameterFields(
        **raw.model_dump(),
        parsing_version=EXTRACTOR_VERSION,
        alias_version=RULES_VERSION,
        canonical_metric=ALIASES.get(key(raw.original_label)),
        value_kind="missing",
        source_flag=source_flag,
    )
    if value is not None:
        match = NUMERIC.fullmatch(value)
        if match:
            result.value_kind = "numeric"
            result.numeric_value = decimal_text(match["num"])
            result.comparator = cast(
                Literal["<", ">", "<=", ">=", "=", "≤", "≥"] | None, match["cmp"]
            )
        elif key(value) in QUALITATIVE:
            result.value_kind = "qualitative"
            result.qualitative_result = value
        elif re.fullmatch(r"[0-9]{1,10}:[0-9]{1,10}", value):
            result.value_kind = "titre"
        elif RANGE.fullmatch(value):
            result.value_kind = "interval"
        elif re.fullmatch(r"[0-9]{1,2}\+", value):
            result.value_kind = "ordinal"
        else:
            result.value_kind = "unparsed"
    reference = raw.raw_reference
    if reference:
        interval = RANGE.fullmatch(reference)
        single = NUMERIC.fullmatch(reference)
        up_to = re.fullmatch(rf"(?i:up to)\s+({NUMBER})", reference)
        if interval and Decimal(interval[1].replace("−", "-")) <= Decimal(
            interval[2].replace("−", "-")
        ):
            result.reference_low, result.reference_high = (
                decimal_text(interval[1]),
                decimal_text(interval[2]),
            )
            result.reference_low_inclusive = result.reference_high_inclusive = True
        elif single and single["cmp"] in {"<", "<=", "≤"}:
            result.reference_high = decimal_text(single["num"])
            result.reference_high_inclusive = single["cmp"] != "<"
        elif single and single["cmp"] in {">", ">=", "≥"}:
            result.reference_low = decimal_text(single["num"])
            result.reference_low_inclusive = single["cmp"] != ">"
        elif up_to:
            result.reference_high, result.reference_high_inclusive = decimal_text(up_to[1]), True
    return result


def header(line: str) -> list[str] | None:
    if "|" in line:
        cells = [HEADERS.get(key(cell), "invalid") for cell in line.split("|")]
        if (
            cells[:2] == ["label", "value"]
            and len(set(cells)) == len(cells)
            and "invalid" not in cells
        ):
            return cells
        return None
    # Compact headers have an intentionally small explicit grammar.
    match = re.fullmatch(
        r"(?i)(parameter|test|test name|sample label|investigation) (result|value)"
        r"( units?)?( reference(?: range)?)?( flag)?",
        line,
    )
    if not match:
        return None
    return (
        ["label", "value"]
        + (["unit"] if match[3] else [])
        + (["reference"] if match[4] else [])
        + (["flag"] if match[5] else [])
    )


def compact_parts(line: str, columns: list[str]) -> dict[str, str] | None:
    # Enumerate token boundaries; reject rather than choose between valid bindings.
    words = line.split(" ")
    options: list[dict[str, str]] = []
    for boundary in range(1, min(len(words), 20)):
        label = " ".join(words[:boundary])
        if any(NUMERIC.fullmatch(word) for word in words[:boundary]):
            continue
        if len(label) > 160 or not any(c.isalpha() for c in label):
            continue
        for length in (1, 2, 3):
            value = " ".join(words[boundary : boundary + length])
            if fields(RawFields(original_label=label, raw_value=value)).value_kind in {
                "unparsed",
                "missing",
            }:
                continue
            rest = words[boundary + length :]
            row = {"label": label, "value": value}
            if "flag" in columns and rest and rest[-1] in FLAGS:
                row["flag"] = rest.pop()
            if (
                "unit" in columns
                and rest
                and re.fullmatch(
                    r"(?:[%]|[A-Za-zµμ][A-Za-z0-9µμ/%^³².-]{0,40}|10(?:\^[0-9]+|[³⁶⁹])/[A-Za-zµμ]+)",
                    rest[0],
                )
                and rest[0] not in {"Up", "Negative", "Male:", "Female:"}
            ):
                row["unit"] = rest.pop(0)
            if rest and "reference" in columns:
                reference = " ".join(rest)
                if (
                    RANGE.fullmatch(reference)
                    or NUMERIC.fullmatch(reference)
                    or re.fullmatch(rf"(?i:up to) {NUMBER}", reference)
                    or key(reference) in QUALITATIVE
                ):
                    row["reference"] = reference
                    rest = []
            if not rest:
                # Without explicit cell boundaries, require the printed columns.
                # Otherwise footer text like "Source page 1" becomes a false row.
                if "unit" in columns and "unit" not in row:
                    continue
                options.append(row)
    unique = {tuple(sorted(row.items())) for row in options}
    return dict(next(iter(unique))) if len(unique) == 1 else None


def parse(pages: list[ExtractedPage]) -> tuple[list[CandidateContent], list[str]]:
    if len(pages) > 20 or sum(len(page.text) for page in pages) > 400000:
        raise ParserLimit
    deadline = time.monotonic() + 5
    candidates: list[CandidateContent] = []
    notices: set[str] = set()
    for page in pages:
        columns: list[str] | None = None
        pipe = False
        offset = 0
        pending: tuple[str, int] | None = None
        for physical in page.text.splitlines(keepends=True):
            if time.monotonic() > deadline:
                raise ParserLimit
            start, offset = offset, offset + len(physical)
            line = physical.rstrip("\r\n")
            if len(line) > 512:
                columns, pending = None, None
                notices.add("row_limit_or_ambiguous_layout")
                continue
            found_header = header(line)
            if found_header:
                columns, pipe, pending = found_header, "|" in line, None
                continue
            # Repeated side-by-side headers or section boundaries reset the grammar.
            if not line.strip() or ("result" in key(line) and "test" in key(line)):
                columns, pending = None, None
                continue
            if columns is None:
                continue
            row: dict[str, str] | None = None
            if pipe:
                cells = [cell.strip() for cell in line.split("|")]
                if len(cells) == len(columns):
                    row = dict(zip(columns, cells, strict=True))
            else:
                row = compact_parts(line, columns)
            if row is None:
                pending = (
                    (line, start)
                    if key(line) and any(alias.startswith(key(line) + " ") for alias in ALIASES)
                    else None
                )
                notices.add("unparsed_rows")
                if pending is None and key(line) not in ALIASES:
                    columns = None
                continue
            if pending and key(pending[0] + " " + row["label"]) in ALIASES:
                row["label"] = pending[0] + "\n" + row["label"]
                start = pending[1]
            pending = None
            if not row["label"] or not any(c.isalpha() for c in row["label"]):
                notices.add("unparsed_rows")
                continue
            try:
                raw = RawFields(
                    original_label=row["label"],
                    raw_value=row.get("value") or None,
                    original_unit=row.get("unit") or None,
                    raw_reference=row.get("reference") or None,
                )
            except ValueError:
                notices.add("unparsed_rows")
                continue
            value = fields(raw, row.get("flag") if row.get("flag") in FLAGS else None)
            end = offset - (len(physical) - len(line))
            quote = page.text[start:end]
            indices = [i for i, span in enumerate(page.spans) if span.text == quote]
            # Only exact native-line matches are linked. OCR words may repeat; no guessed indices.
            if len(indices) != 1:
                indices = []
            warnings = ["machine_candidate"]
            if value.canonical_metric is None:
                warnings.append("unmapped_label")
            if value.value_kind in {"unparsed", "missing"}:
                warnings.append("unparsed_or_missing_value")
            if raw.original_unit is None:
                warnings.append("no_unit")
            if raw.raw_reference is None:
                warnings.append("no_reference")
            elif value.reference_low is None and value.reference_high is None:
                warnings.append("unparsed_reference")
            if page.method == "ocr":
                warnings.append("ocr_source_verify_original")
            if not indices:
                warnings.append("text_provenance_only")
            candidates.append(
                CandidateContent(
                    fields=value,
                    page_number=page.page_number,
                    source_text=quote,
                    source_start=start,
                    source_end=end,
                    span_indices=indices,
                    source_method=page.method,
                    ocr_confidence=page.confidence if page.method == "ocr" else None,
                    warnings=warnings,
                )
            )
            if len(candidates) > 200:
                raise ParserLimit
    if not candidates:
        notices.add("unable_to_reliably_extract")
    return candidates, sorted(notices)
