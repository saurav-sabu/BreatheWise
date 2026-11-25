import json
import logging
from typing import Any, Dict, List

from app.schemas.advisor import ObservabilitySummary

logger = logging.getLogger("breathewise.observability")

SENSITIVE_KEYS = {"respiratory_conditions", "name", "api_key", "gemini_api_key", "cpcb_api_key"}


def redact_sensitive(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow-redacted copy of telemetry metadata excluding personal health/secret keys."""
    clean: Dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_KEYS:
            clean[key] = "[REDACTED]"
        else:
            clean[key] = value
    return clean


def log_pipeline_telemetry(event_name: str, summary: ObservabilitySummary, extra: Dict[str, Any] | None = None) -> None:
    """Emit structured JSON log for AI pipeline execution without sensitive personal data."""
    record = {
        "event": event_name,
        "generation_mode": summary.generation_mode,
        "retrieval_mode_used": summary.retrieval_mode_used,
        "embedding_provider": summary.embedding_provider,
        "fallback_activated": summary.fallback_activated,
        "llm_latency_ms": summary.llm_latency_ms,
        "embedding_latency_ms": summary.embedding_latency_ms,
        "retrieval_latency_ms": summary.retrieval_latency_ms,
        "total_latency_ms": summary.total_latency_ms,
        "token_usage": summary.token_usage,
        "nodes_executed": summary.nodes_executed,
        "provider_error_count": len(summary.provider_errors),
    }
    if extra:
        record["context"] = redact_sensitive(extra)
    logger.info(json.dumps(record, default=str))
