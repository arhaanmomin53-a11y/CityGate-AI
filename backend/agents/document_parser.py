"""
Agent 2: Document Parser — OCR + layout analysis for municipal forms/notices.
"""
from backend.skills.ocr_engine import extract_document, get_form_mapping_schema
from backend.skills.pii_vault import vault_text


def parse_document(image_source: str, text_hint: str = "") -> dict:
    """Parse a document photo/PDF and vault any PII in extracted fields."""
    ocr_result = extract_document(image_source, text_hint)

    vaulted_fields = []
    for field in ocr_result["fields"]:
        if field.get("value"):
            vault = vault_text(field["value"])
            if vault["vaulted_count"] > 0:
                field["value_tokenized"] = vault["tokenized_text"]
                field["pii_vaulted"] = True
                vaulted_fields.append(field["field_id"])
            else:
                field["pii_vaulted"] = False

    return {
        "agent": "document_parser",
        "status": "completed",
        "document_id": ocr_result["document_id"],
        "form_type": ocr_result["form_type"],
        "fields": ocr_result["fields"],
        "layout": ocr_result["layout"],
        "metadata": ocr_result["metadata"],
        "schema_version": get_form_mapping_schema()["$schema"],
        "pii_fields_vaulted": vaulted_fields,
        "field_count": len(ocr_result["fields"]),
    }
