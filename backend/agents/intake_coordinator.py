"""
Agent 1: Intake Coordinator — multilingual NLP + PII vaulting before external calls.
"""
import re
from typing import Optional

from backend.skills.pii_vault import vault_text

LANGUAGE_PATTERNS = {
    "es": re.compile(r"\b(necesito|permiso|licencia|negocio|restaurante|dirección|teléfono|aplicar|solicitud)\b", re.I),
    "vi": re.compile(r"\b(giấy phép|kinh doanh|nhà hàng|địa chỉ|xin|cần|đăng ký)\b", re.I),
    "ar": re.compile(r"[\u0600-\u06FF]"),
}

MULTILINGUAL_EXTRACTORS = {
    "es": {
        "business_name": [r"(?:negocio|empresa|llamado|nombre)[:\s]+([A-Za-zÀ-ÿ\s&\.]+)", r"([A-Za-zÀ-ÿ\s&\.]+(?:LLC|Inc|S\.A\.))"],
        "zip_code": [r"\b(\d{5})\b"],
        "city": [r"(?:ciudad|en)\s+([A-Za-zÀ-ÿ\s]+?)(?:,|\s+\d{5}|$)"],
        "phone": [r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"],
    },
    "vi": {
        "business_name": [r"(?:tên|cửa hàng|nhà hàng)\s+([A-Za-zÀ-ÿ\s&\.]+)"],
        "zip_code": [r"\b(\d{5})\b"],
        "phone": [r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"],
    },
    "ar": {
        "business_name": [r"([\u0600-\u06FF\s]+(?:LLC|شركة))"],
        "zip_code": [r"\b(\d{5})\b"],
    },
    "en": {
        "business_name": [r"(?:business|company|called|named)\s+([A-Za-z\s&\.]+(?:LLC|Inc|Corp)?)", r"([A-Za-z\s&\.]+(?:LLC|Inc))"],
        "owner_name": [r"(?:owner|applicant|my name is)\s+([A-Za-z\s\.]+)", r"I(?:'m| am)\s+([A-Za-z\s\.]+)"],
        "business_address": [r"(?:address|located at|at)\s+(\d+[^,\n]+(?:,\s*(?:Suite|Ste|Unit)\s*[A-Z0-9]+)?)", r"(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Blvd|Road|Rd)[^,\n]*)"],
        "zip_code": [r"\b(\d{5})\b"],
        "city": [r"(?:city|in)\s+([A-Za-z\s]+?)(?:,|\s+\d{5}|$)", r"([A-Za-z\s]+),\s*(?:TX|CA|FL|NY)\s+\d{5}"],
        "business_type": [r"(?:restaurant|retail|salon|food truck|bakery|shop)", r"(?:NAICS|type)[:\s]+([^\n\.]+)"],
        "phone": [r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"],
        "tax_id": [r"(?:EIN|tax id|tin)[:\s#]*(\d{2}-\d{7})", r"\b(\d{2}-\d{7})\b"],
    },
}

PRESET_INTAKES = {
    "restaurant_en": {
        "text": "Hi, I need a business license for my restaurant called La Cocina Familiar LLC. I'm Maria Rodriguez, located at 4521 Main Street Suite B, San Antonio TX 78205. My phone is (210) 555-0142 and EIN is 12-3456789.",
        "language": "en",
    },
    "restaurant_es": {
        "text": "Hola, necesito un permiso de negocio para mi restaurante La Cocina Familiar LLC. Soy Maria Rodriguez, en 4521 Main Street Suite B, San Antonio 78205. Teléfono (210) 555-0142.",
        "language": "es",
    },
    "retail_vi": {
        "text": "Xin giấy phép kinh doanh cho cửa hàng Oak Market tại 890 Commerce Blvd, zip 78205. Số điện thoại (210) 555-0199.",
        "language": "vi",
    },
}


def detect_language(text: str) -> str:
    if LANGUAGE_PATTERNS["ar"].search(text):
        return "ar"
    if LANGUAGE_PATTERNS["vi"].search(text):
        return "vi"
    if LANGUAGE_PATTERNS["es"].search(text) or re.search(r"[áéíóúñ¿¡]", text, re.I):
        return "es"
    return "en"


def extract_fields(text: str, language: str) -> dict:
    extractors = MULTILINGUAL_EXTRACTORS.get(language, MULTILINGUAL_EXTRACTORS["en"])
    fields = {}
    for field_id, patterns in extractors.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                val = match.group(1).strip() if match.lastindex else match.group(0).strip()
                fields[field_id] = val
                break
    return fields


def process_intake(text: str, language_override: Optional[str] = None) -> dict:
    """Full intake pipeline: detect language, extract fields, vault PII."""
    language = language_override or detect_language(text)
    extracted = extract_fields(text, language)
    vault_result = vault_text(text)

    return {
        "agent": "intake_coordinator",
        "status": "completed",
        "language_detected": language,
        "original_text_length": len(text),
        "extracted_fields": extracted,
        "tokenized_text": vault_result["tokenized_text"],
        "pii_vaulted": vault_result["vaulted_count"],
        "vault_tokens": vault_result["tokens"],
        "session_id": vault_result["session_id"],
        "confidence": min(0.95, 0.6 + len(extracted) * 0.05),
    }
