"""
PDF Form Filler Skill — programmatically populates official permit PDF fields
from refined JSON conversation data.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "filled_forms")

OFFICIAL_FORMS = {
    "business_license": {
        "form_id": "SA-BL-2024",
        "title": "City Business License Application",
        "official_fields": [
            {"field_id": "business_name", "label": "Business Legal Name", "required": True, "type": "text"},
            {"field_id": "owner_name", "label": "Owner / Applicant Name", "required": True, "type": "text"},
            {"field_id": "business_address", "label": "Business Address", "required": True, "type": "text"},
            {"field_id": "city", "label": "City", "required": True, "type": "text"},
            {"field_id": "zip_code", "label": "ZIP Code", "required": True, "type": "text"},
            {"field_id": "business_type", "label": "Business Type / NAICS", "required": True, "type": "text"},
            {"field_id": "tax_id", "label": "Federal Tax ID (EIN)", "required": True, "type": "text", "pii": True},
            {"field_id": "phone", "label": "Contact Phone", "required": True, "type": "text", "pii": True},
        ],
    },
    "zoning_permit": {
        "form_id": "SA-ZP-2024",
        "title": "Zoning Permit Application",
        "official_fields": [
            {"field_id": "property_address", "label": "Property Address", "required": True, "type": "text"},
            {"field_id": "parcel_id", "label": "Parcel / APN", "required": True, "type": "text"},
            {"field_id": "proposed_use", "label": "Proposed Use", "required": True, "type": "text"},
            {"field_id": "zoning_district", "label": "Current Zoning", "required": True, "type": "text"},
        ],
    },
}


def build_form_comparison(parsed_fields: list, intake_data: dict, form_type: str = "business_license") -> dict:
    """Build side-by-side comparison for HITL approval modal."""
    form_def = OFFICIAL_FORMS.get(form_type, OFFICIAL_FORMS["business_license"])
    field_map = {f["field_id"]: f["value"] for f in parsed_fields}
    intake_map = intake_data.get("extracted_fields", {})

    comparison = []
    for official in form_def["official_fields"]:
        fid = official["field_id"]
        agent_value = field_map.get(fid) or intake_map.get(fid) or ""
        comparison.append({
            "field_id": fid,
            "form_asks": official["label"],
            "agent_filled": agent_value,
            "required": official["required"],
            "pii": official.get("pii", False),
            "match": bool(agent_value),
        })

    return {
        "form_id": form_def["form_id"],
        "form_title": form_def["title"],
        "comparison": comparison,
        "ready_for_submission": all(c["match"] for c in comparison if c["required"]),
        "filled_count": sum(1 for c in comparison if c["match"]),
        "total_fields": len(comparison),
    }


def fill_pdf_form(comparison_data: dict, approved: bool = False) -> dict:
    """Generate filled form artifact (mock PDF output for development)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    form_id = comparison_data.get("form_id", "UNKNOWN")
    submission_id = f"SUB-{uuid.uuid4().hex[:8].upper()}"

    filled = {
        "submission_id": submission_id,
        "form_id": form_id,
        "form_title": comparison_data.get("form_title"),
        "fields": {c["field_id"]: c["agent_filled"] for c in comparison_data.get("comparison", [])},
        "approved_by_human": approved,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "submitted" if approved else "draft",
    }

    out_path = os.path.join(OUTPUT_DIR, f"{submission_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(filled, f, indent=2)

    return {
        "submission_id": submission_id,
        "output_path": out_path,
        "status": filled["status"],
        "field_count": len(filled["fields"]),
    }
