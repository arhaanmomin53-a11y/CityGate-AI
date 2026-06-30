# PDF Form Filler Skill

Programmatically populates official PDF permit application fields from refined JSON data.

## Usage
```python
from backend.skills.form_filler import build_form_comparison, fill_pdf_form
comparison = build_form_comparison(parsed_fields, intake_data, "business_license")
result = fill_pdf_form(comparison, approved=True)  # Only after HITL approval
```

## HITL Requirement
Form submission requires explicit human approval via the dashboard modal.
