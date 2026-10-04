"""One owner-authorized synthetic request, no app server, database or Storage access.

Run as a module from backend. Only --live sends; default is offline preflight.
No raw provider output, credentials, headers or exception text is printed or saved.
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.ai_config import AISettings
from app.core.errors import ApiProblem
from app.core.explanation_context import facts, render_output, validate_output
from app.core.explanation_provider import GenerationPermit, context_digest, request_body
from app.core.openai_acceptance import (
    ACCEPTANCE_MODEL,
    ACCEPTANCE_OUTPUT_TOKENS,
    ACCEPTANCE_REQUEST_BYTES,
    OneShotOpenAITransport,
    create_acceptance_provider,
)
from app.core.parameter_parser import fields
from app.schemas.explanations import SourceEvidence
from app.schemas.parameters import RawFields

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / ".cache" / "phase13" / "openai-acceptance-1"


def synthetic_source() -> SourceEvidence:
    return SourceEvidence(
        observation_id=uuid4(),
        revision=1,
        candidate_id=uuid4(),
        review_revision=1,
        source_run_id=uuid4(),
        parameter_run_id=uuid4(),
        page_number=1,
        source_start=0,
        source_end=40,
        fields=fields(
            RawFields(
                original_label="Vitamin D",
                raw_value="18",
                original_unit="ng/mL",
                raw_reference="30–100",
            )
        ),
    )


def preflight(settings: AISettings) -> dict[str, object]:
    if "RUN_AI_INTEGRATION" in os.environ:
        raise RuntimeError("Live integration must be unset outside the isolated attempt")
    source = synthetic_source()
    context = facts([source])
    provider = create_acceptance_provider(settings, AUDIT / "attempt-reserved.json")
    assert type(provider._transport) is OneShotOpenAITransport
    assert provider.name == "openai" and not provider.assistant_available
    assert not provider.available
    body = request_body(
        context, model=settings.ai_model, max_output_tokens=ACCEPTANCE_OUTPUT_TOKENS
    )
    serialized = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(serialized) <= ACCEPTANCE_REQUEST_BYTES
    assert context[0].value == "18" and context[0].unit == "ng/mL"
    assert context[0].reference == "30–100" and context[0].evidence_id == "e1"
    assert str(source.observation_id).encode() not in serialized
    assert str(source.source_run_id).encode() not in serialized
    assert settings.ai_api_key is not None
    assert settings.ai_api_key.get_secret_value().encode() not in serialized
    return {
        "preflight": "passed",
        "provider": provider.name,
        "requested_model": settings.ai_model,
        "request_bytes": len(serialized),
        "output_token_limit": ACCEPTANCE_OUTPUT_TOKENS,
        # Conservative byte/token + 4096 framing allowance, cache-write rate,
        # and 10% regional margin; no extra token-count or model-list API call.
        "conservative_cost_bound_usd": 0.06,
        "synthetic_fixtures": 1,
        "database_storage_access": False,
        "normal_app_defaults_changed": False,
        "phase9_live_locked": True,
    }


async def attempt(settings: AISettings) -> dict[str, object]:
    result = preflight(settings)
    AUDIT.mkdir(parents=True, exist_ok=True)
    source = synthetic_source()
    context = facts([source])
    provider = create_acceptance_provider(settings, AUDIT / "attempt-reserved.json")
    transport = provider._transport
    assert type(transport) is OneShotOpenAITransport
    # In-memory authorization for this generated fixture, not a DB reservation.
    permit = GenerationPermit(uuid4(), context_digest(context), True, 25)
    result.update(
        timestamp_utc=datetime.now(UTC).isoformat(),
        result="not_sent",
        schema_validation="not_reached",
        evidence_validation="not_reached",
        safety_grounding="not_reached",
        retries=0,
    )
    os.environ["RUN_AI_INTEGRATION"] = "1"
    try:
        generated = await provider.generate(context, permit)
        validated = validate_output(generated.output.model_dump(), context)
        rendered = render_output(validated, [source])
        assert len(rendered) == 1 and rendered[0].fact == context[0]
        result.update(
            result="passed",
            schema_validation="passed",
            evidence_validation="passed",
            safety_grounding="passed",
            input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens,
            # Uncached standard-price estimate; final billing may differ.
            estimated_cost_usd=round(
                (generated.input_tokens * 2 + generated.output_tokens * 10) / 1000000, 6
            ),
            exact_value_preserved=True,
            exact_unit_preserved=True,
            exact_reference_preserved=True,
            opaque_evidence_ids_valid=True,
            closed_educational_contract=True,
        )
    except ApiProblem as error:
        # Application-owned closed error categories, never raw provider messages.
        result.update(result="failed", failure_category=error.code)
        if error.code == "explanation_invalid":
            result.update(schema_evidence_validation="failed")
    except Exception:
        result.update(result="failed", failure_category="local_or_transport_failure")
    finally:
        os.environ.pop("RUN_AI_INTEGRATION", None)
        await transport.aclose()
    result.update(
        outbound_provider_dispatches=transport.calls,
        http_status=provider.http_status,
        provider_error_code=provider.error_code,
        confirmed_provider="openai" if provider.http_status is not None else None,
        confirmed_model=ACCEPTANCE_MODEL if provider.model_confirmed else None,
        live_integration_final="unset",
        gemini_attempts="2/20 unchanged",
        openai_attempts=transport.calls,
    )
    assert settings.ai_api_key is not None
    result["artifact_secret_check"] = "passed"
    serialized = json.dumps(result, ensure_ascii=True, indent=2)
    if settings.ai_api_key.get_secret_value() in serialized or "Bearer " in serialized:
        raise RuntimeError("Artifact privacy check failed")
    with (AUDIT / "result.json").open("x", encoding="utf-8") as output:
        output.write(serialized + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    # No SDK/HTTP debug logs, including on error. This is an isolated CLI process.
    logging.disable(logging.CRITICAL)
    try:
        settings = AISettings()
        result = asyncio.run(attempt(settings)) if args.live else preflight(settings)
    except Exception:
        os.environ.pop("RUN_AI_INTEGRATION", None)
        print('{"result":"stopped","category":"local_preflight_or_audit_failure"}')
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result.get("result") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
