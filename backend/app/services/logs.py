from dataclasses import dataclass
import re
from typing import Any

_SECRET_PATTERNS = (
    re.compile(r"(?i)(\b(?:token|password|passwd|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(\bAuthorization\s*:\s*Bearer\s+)[^\s,;]+"),
    re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?i)([?&](?:token|password|secret|api[_-]?key)=)[^&\s]+"),
)

_ALLOWED_LEVELS = {"debug", "info", "warning", "error", "critical"}


@dataclass(frozen=True)
class NormalizedLog:
    resource_id: str | None
    source: str
    level: str
    message: str
    metadata: dict[str, Any]


def redact_secrets(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]" if match.lastindex else "[REDACTED]", redacted)
    return redacted


def normalize_log(
    *, resource_id: str | None, source: str, level: str, message: str, metadata: dict[str, Any] | None = None
) -> NormalizedLog:
    normalized_level = level.lower() if level.lower() in _ALLOWED_LEVELS else "info"
    normalized_source = redact_secrets(source.strip())[:120] or "unknown"
    normalized_message = redact_secrets(message.strip())[:4000] or "(empty log message)"
    safe_metadata = {str(key): value for key, value in (metadata or {}).items() if str(key).lower() not in {"token", "password", "secret", "api_key"}}
    return NormalizedLog(resource_id, normalized_source, normalized_level, normalized_message, safe_metadata)
