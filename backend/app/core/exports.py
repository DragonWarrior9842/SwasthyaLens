"""Bounded deterministic serialization; no disk, Storage, model or durable artifact."""

import csv
import io
import json
import time
from datetime import UTC

from app.core.auth_service import AuthenticatedRequest
from app.core.errors import ApiProblem
from app.core.observations import ObservationService
from app.schemas.exports import ExportContext, ExportInput, ExportRow

MAX_BYTES = 2 * 1024 * 1024
# Stable machine keys and human-readable labels, without translating original fields.
LABELS = {
    "source_type": ("Source", "स्रोत"),
    "original_label": ("Original label", "मूल नाम"),
    "raw_value": ("Original value", "मूल मान"),
    "original_unit": ("Original unit", "मूल इकाई"),
    "raw_reference": ("Supplied reference range", "दी गई संदर्भ सीमा"),
    "source_flag": ("Supplied flag", "दिया गया संकेत"),
    "comparator": ("Comparator", "तुलना चिह्न"),
    "qualitative_result": ("Qualitative result", "गुणात्मक परिणाम"),
    "value_kind": ("Value type", "मान का प्रकार"),
    "measurement_date": ("Measurement day", "माप की तारीख"),
    "measured_at": ("Measurement time (UTC)", "माप का समय (UTC)"),
    "date_status": ("Date precision", "तारीख की सटीकता"),
    "status": ("Observation status", "अवलोकन की स्थिति"),
    "revision": ("Observation revision", "अवलोकन संशोधन"),
    "report_name": ("Source report", "स्रोत रिपोर्ट"),
    "report_recorded_at": ("Report record created (UTC)", "रिपोर्ट रिकॉर्ड बना (UTC)"),
    "page_number": ("Source page", "स्रोत पृष्ठ"),
    "source_method": ("Extraction method", "निष्कर्षण विधि"),
    "review_action": ("Personal review", "व्यक्तिगत समीक्षा"),
    "review_revision": ("Review revision", "समीक्षा संशोधन"),
}
WORDS = {
    "report": ("From report", "रिपोर्ट से"),
    "manual": ("Manually entered", "मैन्युअल रूप से दर्ज"),
    "unknown": ("Unknown date", "तारीख अज्ञात"),
    "day": ("Day only", "केवल तारीख"),
    "instant": ("Exact time (UTC)", "सटीक समय (UTC)"),
    "active": ("Active", "सक्रिय"),
    "confirmed": ("Personally confirmed", "व्यक्तिगत पुष्टि"),
    "corrected": ("Personally corrected", "व्यक्तिगत सुधार"),
    "native_text": ("Native text", "मूल डिजिटल पाठ"),
    "ocr": ("OCR", "OCR"),
    "numeric": ("Numeric", "संख्यात्मक"),
    "qualitative": ("Qualitative", "गुणात्मक"),
    "titre": ("Titre", "टाइटर"),
    "interval": ("Interval", "अंतराल"),
    "ordinal": ("Ordinal", "क्रमिक"),
    "unparsed": ("Unparsed", "अविश्लेषित"),
    "missing": ("Missing", "अनुपलब्ध"),
}


def unavailable() -> ApiProblem:
    return ApiProblem(503, "export_unavailable", "The export could not be verified. Try again.")


def record(row: ExportRow) -> dict[str, object]:
    result: dict[str, object] = {
        key: getattr(row.fields, key)
        for key in (
            "original_label",
            "raw_value",
            "original_unit",
            "raw_reference",
            "source_flag",
            "comparator",
            "qualitative_result",
            "value_kind",
        )
    }
    result.update(
        {
            key: getattr(row, key)
            for key in (
                "source_type",
                "status",
                "revision",
                "report_name",
                "page_number",
                "source_method",
                "review_action",
                "review_revision",
            )
        }
    )
    result["measurement_date"] = row.measurement_date.isoformat() if row.measurement_date else None
    result["measured_at"] = row.measured_at.astimezone(UTC).isoformat() if row.measured_at else None
    result["report_recorded_at"] = (
        row.report_recorded_at.astimezone(UTC).isoformat() if row.report_recorded_at else None
    )
    result["date_status"] = (
        "instant" if row.measured_at else "day" if row.measurement_date else "unknown"
    )
    return {key: result[key] for key in LABELS}


def serialize(context: ExportContext, body: ExportInput) -> bytes:
    language = 1 if body.language == "hi" else 0
    rows = [record(row) for row in context.items]
    if body.format == "json":
        payload = {
            "version": "health-export-v1",
            "language": body.language,
            "as_of": context.as_of.astimezone(UTC).isoformat(),
            "date_basis": "UTC",
            "period": {
                "from": body.date_from.isoformat(),
                "through": body.date_to.isoformat(),
                "include_unknown": body.include_unknown,
            },
            "labels": {key: labels[language] for key, labels in LABELS.items()},
            "codes": {key: labels[language] for key, labels in WORDS.items()},
            "observations": rows,
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    else:
        output = io.StringIO(newline="")
        writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writerow([labels[language] for labels in LABELS.values()])
        for row in rows:
            cells = []
            for key, value in row.items():
                if key in {
                    "source_type",
                    "date_status",
                    "status",
                    "source_method",
                    "review_action",
                    "value_kind",
                } and isinstance(value, str):
                    value = WORDS[value][language]
                cell = "" if value is None else str(value)
                # Quoting alone does not prevent spreadsheet formula execution.
                # Refuse this format instead of changing any original medical string.
                if cell.lstrip().startswith(("=", "+", "-", "@")) or cell.startswith(
                    ("\t", "\r", "\n")
                ):
                    raise ApiProblem(
                        422,
                        "export_csv_unsafe",
                        "Use JSON for source text that a spreadsheet could interpret as a formula.",
                    )
                cells.append(cell)
            writer.writerow(cells)
        data = output.getvalue().encode("utf-8-sig")
    if len(data) > MAX_BYTES:
        raise ApiProblem(422, "export_capacity", "Choose a smaller export period or source.")
    return data


class ExportService:
    def __init__(self, observations: ObservationService) -> None:
        self.gateway = observations.parameters.extraction.reports.gateway

    def generate(self, body: ExportInput, current: AuthenticatedRequest) -> bytes:
        started = time.monotonic()
        value = self.gateway.object(
            "POST",
            "/rest/v1/rpc/export_context",
            access_token=current.access_token,
            purpose="reports",
            payload={
                "p_from": body.date_from.isoformat(),
                "p_to": body.date_to.isoformat(),
                "p_unknown": body.include_unknown,
                "p_source": body.source_type,
                "p_report": str(body.report_id) if body.report_id else None,
            },
        )
        try:
            context = ExportContext.model_validate(value)
            if context.user_id != current.identity.user_id or len(
                {r.id for r in context.items}
            ) != len(context.items):
                raise ValueError
            if len({r.report_id for r in context.items if r.report_id}) > 20:
                raise ValueError
            for row in context.items:
                day = row.measurement_date or (
                    row.measured_at.astimezone(UTC).date() if row.measured_at else None
                )
                if (
                    row.user_id != current.identity.user_id
                    or (body.source_type and row.source_type != body.source_type)
                    or (body.report_id and row.report_id != body.report_id)
                    or (day is None and not body.include_unknown)
                    or (day is not None and not body.date_from <= day <= body.date_to)
                ):
                    raise ValueError
        except (ValueError, TypeError, KeyError):
            raise unavailable() from None
        data = serialize(context, body)
        if time.monotonic() - started > 15:
            raise ApiProblem(
                504, "export_timeout", "The export took too long. Try a smaller scope."
            )
        return data
