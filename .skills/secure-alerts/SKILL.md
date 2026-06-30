# Secure Alerts Skill

Generates notifications that do not leak PII in push headers.

## Usage
```python
from backend.skills.secure_alerts import create_secure_alert, check_renewal_deadlines
alert = create_secure_alert("renewal_reminder", "License due soon", "Your permit expires in 16 days")
```

## PII Safety
All alert titles and preview bodies are sanitized before delivery.
