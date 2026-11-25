import re
from typing import Tuple

HTML_TAG_RE = re.compile(r"<[^>]+>")
URL_FLOOD_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-]{7,}\d)")
MEDICAL_CLAIM_RE = re.compile(
    r"(?i)\b(cure|cures|prevents?|eliminates?)\s+(asthma|copd|cancer|heart\s+disease|diabetes|covid)\b"
)
BLOCKED_TERMS_RE = re.compile(r"(?i)\b(buy\s+crypto|whatsapp\s+me|click\s+here\s+free|kill\s+yourself)\b")


class ContentModerationError(ValueError):
    """Raised when user-submitted community content violates safety, PII, or spam rules."""


def sanitize_and_validate_community_text(text: str, *, field_name: str = "content") -> str:
    """Strip HTML tags, normalize whitespace, and block PII leaks, spam, or unsafe medical claims."""
    cleaned = HTML_TAG_RE.sub("", text)
    cleaned = " ".join(cleaned.split()).strip()
    if not cleaned:
        raise ContentModerationError(f"{field_name} cannot be empty after sanitization.")

    if EMAIL_RE.search(cleaned) or PHONE_RE.search(cleaned):
        raise ContentModerationError(
            f"{field_name} appears to contain an email address or phone number. Remove personal contact details."
        )

    if len(URL_FLOOD_RE.findall(cleaned)) > 1:
        raise ContentModerationError(f"{field_name} contains too many external links (spam protection).")

    if MEDICAL_CLAIM_RE.search(cleaned):
        raise ContentModerationError(
            f"{field_name} contains unsupported medical cure/prevention claims. Share practical observations or habits only."
        )

    if BLOCKED_TERMS_RE.search(cleaned):
        raise ContentModerationError(f"{field_name} triggered community spam/abuse moderation filters.")

    return cleaned


def evaluate_moderation_status(report_count: int) -> Tuple[str, str]:
    """Determine post moderation status based on cumulative verified user reports."""
    if report_count >= 5:
        return "hidden", "Post automatically hidden pending review after 5 community reports."
    if report_count >= 2:
        return "flagged", "Post flagged and removed from default public feed after multiple reports."
    return "published", "Report recorded; post remains visible pending threshold review."
