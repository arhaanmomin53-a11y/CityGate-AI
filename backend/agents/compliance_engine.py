"""
Agent 3: Compliance Engine — cross-references parsed docs with city code requirements.
"""
from typing import Optional

COMPLIANCE_RULES = {
    "78205": {
        "city": "San Antonio",
        "state": "TX",
        "requirements": [
            {"code": "SA-MC-12.04.010", "title": "Business License Required", "description": "All commercial establishments must hold a valid business license.", "applies_to": ["business_license"]},
            {"code": "SA-MC-12.04.120", "title": "Signage Compliance", "description": "External signage must not exceed 32 sq ft without additional permit.", "applies_to": ["sign_permit", "business_license"]},
            {"code": "SA-MC-15.02.030", "title": "Food Service Health Permit", "description": "Restaurants require health department inspection before license issuance.", "applies_to": ["business_license", "health_permit"]},
            {"code": "SA-MC-08.01.050", "title": "Zoning Use Verification", "description": "Proposed use must match current zoning district classification.", "applies_to": ["zoning_permit", "business_license"]},
        ],
    },
    "90210": {
        "city": "Beverly Hills",
        "state": "CA",
        "requirements": [
            {"code": "BH-MC-5.04.010", "title": "Commercial Business License", "description": "Annual business tax certificate required.", "applies_to": ["business_license"]},
        ],
    },
    "default": {
        "city": "Generic Municipality",
        "state": "US",
        "requirements": [
            {"code": "GEN-MC-001", "title": "General Business License", "description": "Business license required for all commercial activity.", "applies_to": ["business_license"]},
            {"code": "GEN-MC-002", "title": "Zoning Compliance", "description": "Verify zoning district permits proposed business use.", "applies_to": ["zoning_permit", "business_license"]},
        ],
    },
}


def analyze_compliance(
    parsed_document: dict,
    intake_data: dict,
    city_code: dict,
) -> dict:
    """Determine compliance gaps between parsed data and municipal requirements."""
    form_type = parsed_document.get("form_type", "business_license")
    zip_code = _extract_zip(parsed_document, intake_data)
    requirements = city_code.get("requirements", [])

    applicable = [r for r in requirements if form_type in r.get("applies_to", [])]
    extracted = _merge_fields(parsed_document, intake_data)

    gaps = []
    satisfied = []

    required_field_map = {
        "business_license": ["business_name", "owner_name", "business_address", "zip_code", "business_type"],
        "zoning_permit": ["property_address", "parcel_id", "proposed_use", "zoning_district"],
        "municipal_notice": ["notice_type", "violation_code", "deadline"],
    }

    for field_id in required_field_map.get(form_type, []):
        if extracted.get(field_id):
            satisfied.append({"field_id": field_id, "status": "present", "value_preview": extracted[field_id][:30]})
        else:
            gaps.append({
                "gap_id": f"MISSING-{field_id.upper()}",
                "severity": "high",
                "field_id": field_id,
                "description": f"Required field '{field_id}' is missing from application data.",
                "remediation": f"Collect '{field_id}' from applicant during intake.",
            })

    for req in applicable:
        rule_gap = {
            "gap_id": req["code"],
            "severity": "medium",
            "code_reference": req["code"],
            "title": req["title"],
            "description": req["description"],
            "remediation": f"Verify compliance with {req['code']} before submission.",
        }
        if form_type == "business_license" and "restaurant" in str(extracted.get("business_type", "")).lower():
            if req["code"] in ("SA-MC-15.02.030",):
                gaps.append(rule_gap)
            else:
                satisfied.append({"rule": req["code"], "status": "reviewed"})
        else:
            satisfied.append({"rule": req["code"], "status": "applicable"})

    compliance_score = max(0, 100 - len(gaps) * 15)

    return {
        "agent": "compliance_engine",
        "status": "completed",
        "zip_code": zip_code,
        "form_type": form_type,
        "compliance_score": compliance_score,
        "gaps": gaps,
        "satisfied": satisfied,
        "requirements_checked": len(applicable),
        "ready_for_form_fill": len(gaps) == 0 or compliance_score >= 70,
        "city": city_code.get("city", "Unknown"),
    }


def _extract_zip(parsed: dict, intake: dict) -> str:
    for f in parsed.get("fields", []):
        if f.get("field_id") == "zip_code":
            return f.get("value", "")
    return intake.get("extracted_fields", {}).get("zip_code", "78205")


def _merge_fields(parsed: dict, intake: dict) -> dict:
    merged = dict(intake.get("extracted_fields", {}))
    for f in parsed.get("fields", []):
        merged[f["field_id"]] = f.get("value", "")
    return merged
