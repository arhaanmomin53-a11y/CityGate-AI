"""
Agent 4: Advocacy Agent — long-term memory for license lifecycle tracking.
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.skills.secure_alerts import check_renewal_deadlines, create_secure_alert, get_alerts

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "memory")
MEMORY_FILE = os.path.join(MEMORY_DIR, "license_lifecycle.json")

DEFAULT_LICENSES = [
    {
        "license_id": "LIC-001",
        "business_id": "BIZ-LCF-001",
        "business_name": "La Cocina Familiar LLC",
        "license_type": "Business License",
        "issue_date": "2025-06-15",
        "expiry_date": "2026-06-15",
        "days_until_expiry": 351,
        "status": "active",
        "renewal_started": False,
    },
    {
        "license_id": "LIC-002",
        "business_id": "BIZ-LCF-001",
        "business_name": "La Cocina Familiar LLC",
        "license_type": "Health Permit",
        "issue_date": "2025-06-15",
        "expiry_date": "2026-04-01",
        "days_until_expiry": 276,
        "status": "active",
        "renewal_started": False,
    },
    {
        "license_id": "LIC-003",
        "business_id": "BIZ-OM-002",
        "business_name": "Oak Market",
        "license_type": "Business License",
        "issue_date": "2024-07-20",
        "expiry_date": "2026-07-15",
        "days_until_expiry": 16,
        "status": "renewal_due",
        "renewal_started": False,
    },
]


def _ensure_memory() -> list:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_LICENSES, f, indent=2)
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_memory(licenses: list):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=2)


def _refresh_expiry_days(licenses: list) -> list:
    today = datetime.now(timezone.utc).date()
    for lic in licenses:
        try:
            expiry = datetime.strptime(lic["expiry_date"], "%Y-%m-%d").date()
            lic["days_until_expiry"] = (expiry - today).days
            if lic["days_until_expiry"] <= 42:
                lic["status"] = "renewal_due"
        except (KeyError, ValueError):
            pass
    return licenses


def get_license_memory(business_id: Optional[str] = None) -> dict:
    licenses = _refresh_expiry_days(_ensure_memory())
    if business_id:
        licenses = [l for l in licenses if l["business_id"] == business_id]
    return {
        "agent": "advocacy_agent",
        "status": "completed",
        "licenses": licenses,
        "total": len(licenses),
        "renewal_due_count": sum(1 for l in licenses if l.get("status") == "renewal_due"),
    }


def run_proactive_check(business_id: Optional[str] = None) -> dict:
    """Scan all licenses and generate secure renewal alerts."""
    memory = get_license_memory(business_id)
    alerts = check_renewal_deadlines(memory["licenses"])
    return {
        "agent": "advocacy_agent",
        "status": "completed",
        "licenses_scanned": memory["total"],
        "alerts_generated": len(alerts),
        "alerts": alerts,
    }


def register_license(business_name: str, license_type: str, business_id: Optional[str] = None) -> dict:
    licenses = _ensure_memory()
    new_lic = {
        "license_id": f"LIC-{uuid.uuid4().hex[:6].upper()}",
        "business_id": business_id or f"BIZ-{uuid.uuid4().hex[:6].upper()}",
        "business_name": business_name,
        "license_type": license_type,
        "issue_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "expiry_date": (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d"),
        "days_until_expiry": 365,
        "status": "active",
        "renewal_started": False,
    }
    licenses.append(new_lic)
    _save_memory(licenses)
    create_secure_alert(
        "license_registered",
        f"New {license_type} registered",
        f"A new {license_type} has been registered for tracking. Renewal reminders will begin 6 weeks before expiry.",
        business_id=new_lic["business_id"],
    )
    return new_lic
