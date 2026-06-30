"""
PII Vaulting Skill — captures sensitive strings locally, replaces with tokens
before any data leaves the local environment.
"""
import os
import re
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet

VAULT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "vault")
VAULT_DB = os.path.join(VAULT_DIR, "pii_vault.db")
KEY_FILE = os.path.join(VAULT_DIR, ".vault_key")

PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EIN": re.compile(r"\b\d{2}-\d{7}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "TAX_ID": re.compile(r"\b(?:TIN|EIN|SSN|Tax\s*ID)[:\s#]*([A-Z0-9\-]{9,12})\b", re.I),
}


def _ensure_vault() -> Fernet:
    os.makedirs(VAULT_DIR, exist_ok=True)
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    conn = sqlite3.connect(VAULT_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_entries (
            token TEXT PRIMARY KEY,
            pii_type TEXT NOT NULL,
            encrypted_value BLOB NOT NULL,
            value_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    return Fernet(key)


def vault_text(text: str, session_id: Optional[str] = None) -> dict:
    """Scan text for PII, vault locally, return tokenized text."""
    fernet = _ensure_vault()
    conn = sqlite3.connect(VAULT_DB)
    tokenized = text
    vault_count = 0
    tokens_created = []

    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            raw = match.group(0)
            value_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
            token = f"{{{{TOKEN_{pii_type}_VAULT_{secrets.token_hex(4).upper()}}}}}"

            encrypted = fernet.encrypt(raw.encode())
            conn.execute(
                "INSERT OR REPLACE INTO vault_entries (token, pii_type, encrypted_value, value_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (token, pii_type, encrypted, value_hash, datetime.now(timezone.utc).isoformat()),
            )
            tokenized = tokenized.replace(raw, token, 1)
            vault_count += 1
            tokens_created.append({"type": pii_type, "token": token})

    conn.commit()
    conn.close()
    return {
        "original_length": len(text),
        "tokenized_text": tokenized,
        "vaulted_count": vault_count,
        "tokens": tokens_created,
        "session_id": session_id or secrets.token_hex(8),
    }


def unvault_text(tokenized_text: str) -> str:
    """Restore vaulted tokens — local only, never sent externally."""
    fernet = _ensure_vault()
    conn = sqlite3.connect(VAULT_DB)
    restored = tokenized_text
    for row in conn.execute("SELECT token, encrypted_value FROM vault_entries"):
        token, encrypted = row
        if token in restored:
            try:
                plain = fernet.decrypt(encrypted).decode()
                restored = restored.replace(token, plain)
            except Exception:
                pass
    conn.close()
    return restored


def get_vault_stats() -> dict:
    conn = sqlite3.connect(VAULT_DB) if os.path.exists(VAULT_DB) else None
    if not conn:
        return {"total_entries": 0, "by_type": {}}
    by_type = {}
    for row in conn.execute("SELECT pii_type, COUNT(*) FROM vault_entries GROUP BY pii_type"):
        by_type[row[0]] = row[1]
    total = sum(by_type.values())
    conn.close()
    return {"total_entries": total, "by_type": by_type}
