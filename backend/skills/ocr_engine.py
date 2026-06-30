"""
OCR Engine Skill — extracts structured text from municipal notice photos/PDFs.
Uses mock OCR with layout analysis for development; swap in Tesseract/EasyOCR for prod.
"""
import re
import uuid
from typing import Optional

FORM_MAPPING_SCHEMA = {
    "$schema": "https://citygate.local/schemas/form-mapping/v1",
    "type": "object",
    "required": ["document_id", "form_type", "fields", "layout", "metadata"],
    "properties": {
        "document_id": {"type": "string"},
        "form_type": {"type": "string", "enum": ["business_license", "zoning_permit", "health_permit", "sign_permit", "municipal_notice"]},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["field_id", "label", "value", "confidence", "bbox"],
                "properties": {
                    "field_id": {"type": "string"},
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "bbox": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "w": {"type": "number"}, "h": {"type": "number"}}},
                },
            },
        },
        "layout": {
            "type": "object",
            "properties": {
                "pages": {"type": "integer"},
                "regions": {"type": "array", "items": {"type": "string"}},
                "reading_order": {"type": "array", "items": {"type": "string"}},
            },
        },
        "metadata": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "language_detected": {"type": "string"},
                "ocr_engine": {"type": "string"},
            },
        },
    },
}

MOCK_OCR_SAMPLES = {
    "business_license": {
        "form_type": "business_license",
        "fields": [
            {"field_id": "business_name", "label": "Business Legal Name", "value": "La Cocina Familiar LLC", "confidence": 0.94, "bbox": {"x": 120, "y": 85, "w": 340, "h": 28}},
            {"field_id": "owner_name", "label": "Owner / Applicant Name", "value": "Maria Rodriguez", "confidence": 0.91, "bbox": {"x": 120, "y": 130, "w": 280, "h": 28}},
            {"field_id": "business_address", "label": "Business Address", "value": "4521 Main Street, Suite B", "confidence": 0.88, "bbox": {"x": 120, "y": 175, "w": 400, "h": 28}},
            {"field_id": "city", "label": "City", "value": "San Antonio", "confidence": 0.96, "bbox": {"x": 120, "y": 220, "w": 180, "h": 28}},
            {"field_id": "zip_code", "label": "ZIP Code", "value": "78205", "confidence": 0.97, "bbox": {"x": 320, "y": 220, "w": 80, "h": 28}},
            {"field_id": "business_type", "label": "Business Type / NAICS", "value": "722511 - Full-Service Restaurant", "confidence": 0.85, "bbox": {"x": 120, "y": 265, "w": 350, "h": 28}},
            {"field_id": "tax_id", "label": "Federal Tax ID (EIN)", "value": "12-3456789", "confidence": 0.82, "bbox": {"x": 120, "y": 310, "w": 150, "h": 28}},
            {"field_id": "phone", "label": "Contact Phone", "value": "(210) 555-0142", "confidence": 0.90, "bbox": {"x": 120, "y": 355, "w": 160, "h": 28}},
        ],
        "layout": {"pages": 1, "regions": ["header", "applicant_info", "business_details", "signature_block"], "reading_order": ["header", "applicant_info", "business_details", "signature_block"]},
    },
    "zoning_permit": {
        "form_type": "zoning_permit",
        "fields": [
            {"field_id": "property_address", "label": "Property Address", "value": "890 Commerce Blvd", "confidence": 0.93, "bbox": {"x": 100, "y": 90, "w": 380, "h": 28}},
            {"field_id": "parcel_id", "label": "Parcel / APN", "value": "R-12345-678", "confidence": 0.89, "bbox": {"x": 100, "y": 140, "w": 200, "h": 28}},
            {"field_id": "proposed_use", "label": "Proposed Use", "value": "Retail - General Merchandise", "confidence": 0.87, "bbox": {"x": 100, "y": 190, "w": 350, "h": 28}},
            {"field_id": "zoning_district", "label": "Current Zoning", "value": "C-2 Commercial", "confidence": 0.92, "bbox": {"x": 100, "y": 240, "w": 200, "h": 28}},
        ],
        "layout": {"pages": 2, "regions": ["cover", "site_plan", "use_description"], "reading_order": ["cover", "site_plan", "use_description"]},
    },
    "municipal_notice": {
        "form_type": "municipal_notice",
        "fields": [
            {"field_id": "notice_type", "label": "Notice Type", "value": "Code Violation - Signage", "confidence": 0.91, "bbox": {"x": 80, "y": 60, "w": 420, "h": 32}},
            {"field_id": "violation_code", "label": "Ordinance Reference", "value": "Municipal Code § 12.04.120", "confidence": 0.88, "bbox": {"x": 80, "y": 110, "w": 300, "h": 28}},
            {"field_id": "deadline", "label": "Compliance Deadline", "value": "2026-08-15", "confidence": 0.95, "bbox": {"x": 80, "y": 160, "w": 180, "h": 28}},
            {"field_id": "property", "label": "Subject Property", "value": "1200 Oak Avenue", "confidence": 0.90, "bbox": {"x": 80, "y": 210, "w": 350, "h": 28}},
        ],
        "layout": {"pages": 1, "regions": ["notice_header", "violation_details", "compliance_instructions"], "reading_order": ["notice_header", "violation_details", "compliance_instructions"]},
    },
}


def detect_form_type(image_hint: str, text_hint: Optional[str] = None) -> str:
    hint = (image_hint + " " + (text_hint or "")).lower()
    if "zoning" in hint or "parcel" in hint:
        return "zoning_permit"
    if "notice" in hint or "violation" in hint or "ordinance" in hint:
        return "municipal_notice"
    if "sign" in hint:
        return "sign_permit"
    if "health" in hint:
        return "health_permit"
    return "business_license"


def extract_document(image_source: str, text_hint: Optional[str] = None) -> dict:
    """Run OCR + layout analysis on a document photo or PDF path."""
    form_type = detect_form_type(image_source, text_hint)
    sample = MOCK_OCR_SAMPLES.get(form_type, MOCK_OCR_SAMPLES["business_license"])

    doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    result = {
        "document_id": doc_id,
        "form_type": sample["form_type"],
        "fields": sample["fields"],
        "layout": sample["layout"],
        "metadata": {
            "source": image_source,
            "language_detected": _detect_language(text_hint or ""),
            "ocr_engine": "citygate-ocr-v1 (mock)",
            "raw_text_blocks": len(sample["fields"]),
        },
    }
    return result


def _detect_language(text: str) -> str:
    if re.search(r"[áéíóúñ¿¡]", text, re.I):
        return "es"
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    if re.search(r"[\u0100-\u024F\u1EA0-\u1EF9]", text):
        return "vi"
    return "en"


def get_form_mapping_schema() -> dict:
    return FORM_MAPPING_SCHEMA
