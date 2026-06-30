"""
MCP Server — city code lookup tool for municipal regulatory requirements.
"""
from typing import Optional

MOCK_CITY_CODES = {
    "78205": {
        "zip_code": "78205",
        "city": "San Antonio",
        "state": "TX",
        "county": "Bexar",
        "municipality_code_url": "https://library.municode.com/tx/san_antonio/codes/code_of_ordinances",
        "requirements": [
            {"code": "SA-MC-12.04.010", "title": "Business License Required", "description": "All commercial establishments must hold a valid business license.", "applies_to": ["business_license"], "fee_usd": 150},
            {"code": "SA-MC-12.04.120", "title": "Signage Compliance", "description": "External signage must not exceed 32 sq ft without additional permit.", "applies_to": ["sign_permit", "business_license"], "fee_usd": 75},
            {"code": "SA-MC-15.02.030", "title": "Food Service Health Permit", "description": "Restaurants require health department inspection before license issuance.", "applies_to": ["business_license", "health_permit"], "fee_usd": 250},
            {"code": "SA-MC-08.01.050", "title": "Zoning Use Verification", "description": "Proposed use must match current zoning district classification.", "applies_to": ["zoning_permit", "business_license"], "fee_usd": 0},
        ],
        "permit_office": {"phone": "(210) 207-0133", "hours": "Mon-Fri 8AM-5PM", "address": "1901 S Alamo St, San Antonio, TX 78204"},
    },
    "90210": {
        "zip_code": "90210",
        "city": "Beverly Hills",
        "state": "CA",
        "county": "Los Angeles",
        "requirements": [
            {"code": "BH-MC-5.04.010", "title": "Commercial Business License", "description": "Annual business tax certificate required.", "applies_to": ["business_license"], "fee_usd": 500},
        ],
        "permit_office": {"phone": "(310) 285-1141", "hours": "Mon-Thu 7:30AM-5:30PM", "address": "455 N Rexford Dr, Beverly Hills, CA 90210"},
    },
}

DEFAULT_CITY = {
    "zip_code": "00000",
    "city": "Generic Municipality",
    "state": "US",
    "requirements": [
        {"code": "GEN-MC-001", "title": "General Business License", "description": "Business license required for all commercial activity.", "applies_to": ["business_license"], "fee_usd": 100},
        {"code": "GEN-MC-002", "title": "Zoning Compliance", "description": "Verify zoning district permits proposed business use.", "applies_to": ["zoning_permit", "business_license"], "fee_usd": 0},
    ],
    "permit_office": {"phone": "311", "hours": "Mon-Fri 9AM-5PM", "address": "City Hall"},
}


def mcp_fetch_city_code(zip_code: str, form_type: Optional[str] = None) -> dict:
    """MCP tool: query municipal code database by ZIP code."""
    data = MOCK_CITY_CODES.get(zip_code, {**DEFAULT_CITY, "zip_code": zip_code})
    requirements = data.get("requirements", [])
    if form_type:
        requirements = [r for r in requirements if form_type in r.get("applies_to", [])]

    total_fees = sum(r.get("fee_usd", 0) for r in requirements)

    return {
        "tool": "mcp_fetch_city_code",
        "status": "success",
        "source": "mock_municipal_code_db",
        "zip_code": zip_code,
        "city": data.get("city"),
        "state": data.get("state"),
        "county": data.get("county"),
        "requirements": requirements,
        "total_estimated_fees_usd": total_fees,
        "permit_office": data.get("permit_office"),
        "code_url": data.get("municipality_code_url"),
    }


def mcp_verify_permit_status(permit_id: str) -> dict:
    """MCP tool: verify permit application status."""
    statuses = {
        "pending": {"status": "pending", "stage": "Under Review", "estimated_days": 14},
        "approved": {"status": "approved", "stage": "Approved — Ready for Pickup", "estimated_days": 0},
        "review": {"status": "in_review", "stage": "Compliance Review", "estimated_days": 7},
    }
    mock = statuses.get(permit_id.lower(), statuses["pending"])
    return {
        "tool": "mcp_verify_permit_status",
        "permit_id": permit_id,
        **mock,
        "last_updated": "2026-06-29T12:00:00Z",
    }


MCP_TOOLS = [
    {"name": "mcp_fetch_city_code", "description": "Query municipal code by ZIP code", "parameters": ["zip_code", "form_type"]},
    {"name": "mcp_verify_permit_status", "description": "Verify permit application status", "parameters": ["permit_id"]},
]
