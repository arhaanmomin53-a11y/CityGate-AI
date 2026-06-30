# PII Vaulting Skill

Captures sensitive strings (Tax IDs, SSN, phone numbers) and stores them in a locally encrypted SQLite database.

## Usage
```python
from backend.skills.pii_vault import vault_text, unvault_text
result = vault_text("My EIN is 12-3456789")
# result["tokenized_text"] => "My EIN is {{TOKEN_EIN_VAULT_ABCD1234}}"
```

## Security
- Fernet symmetric encryption
- Local-only storage in `data/vault/pii_vault.db`
- Tokens replace PII before any external API call
