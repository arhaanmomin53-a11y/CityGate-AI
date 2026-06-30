# OCR Engine Skill

Extracts structured text from smartphone photographs of municipal notices or PDF forms.

## Usage
```python
from backend.skills.ocr_engine import extract_document, get_form_mapping_schema
result = extract_document("business_license", text_hint="restaurant permit")
```

## Output Schema
See `get_form_mapping_schema()` for the foundational JSON schema for form mapping.
