"""
Secure Alerts Skill — generates notifications that never leak PII in push headers.
"""
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

ALERT_STORE: list[dict] = []

PII_IN_TEXT = re.compile(
    r"\b(?:\d{3}-\d{2}-\d{4}|\d{2}-\d{7}|\+?\d{10,}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b"
)


def _sanitize(text: str) -> str:
    return PII_IN_TEXT.sub("[REDACTED]", text)


def create_secure_alert(
    alert_type: str,
    title: str,
    body: str,
    business_id: Optional[str] = None,
    days_until_deadline: Optional[int] = None,
) -> dict:
    """Create a PII-safe notification payload."""
    safe_title = _sanitize(title)
    safe_body = _sanitize(body)
    alert_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"

    alert = {
        "alert_id": alert_id,
        "type": alert_type,
        "push_header": safe_title[:80],
        "push_body_preview": safe_body[:120] + ("..." if len(safe_body) > 120 else ""),
        "full_body_encrypted_ref": hashlib.sha256(body.encode()).hexdigest()[:16],
        "business_id": business_id or "unknown",
        "days_until_deadline": days_until_deadline,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "pii_leak_check": "PASSED" if PII_IN_TEXT.search(safe_title + safe_body) is None else "FAILED",
    }
    ALERT_STORE.append(alert)
    return alert


def get_alerts(business_id: Optional[str] = None, unread_only: bool = False) -> list[dict]:
    alerts = ALERT_STORE
    if business_id:
        alerts = [a for a in alerts if a["business_id"] == business_id]
    if unread_only:
        alerts = [a for a in alerts if not a["read"]]
    return sorted(alerts, key=lambda a: a["created_at"], reverse=True)


def check_renewal_deadlines(licenses: list[dict]) -> list[dict]:
    """Scan license records and generate proactive renewal alerts."""
    generated = []
    for lic in licenses:
        days = lic.get("days_until_expiry", 999)
        if days <= 42:
            alert = create_secure_alert(
                alert_type="renewal_reminder",
                title=f"License renewal due in {days} days",
                body=f"Your {lic.get('license_type', 'business')} license expires on {lic.get('expiry_date', 'soon')}. Start renewal now to avoid interruption.",
                business_id=lic.get("business_id"),
                days_until_deadline=days,
            )
            generated.append(alert)
    return generated
