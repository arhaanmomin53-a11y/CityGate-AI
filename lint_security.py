import os
import sys
import re

class SecurityViolationException(Exception):
    """Exception raised when hardcoded credentials or sensitive data are found in code."""
    pass

# Compile regex patterns for sensitive data
SENSITIVE_PATTERNS = {
    "Hardcoded API Key/Token": re.compile(
        r"(?i)(api_key|apikey|secret_key|secret|auth_token|jwt_secret)\s*=\s*['\"][a-zA-Z0-9_]{32,}['\"]"
    ),
    "Hardcoded Password": re.compile(
        r"(?i)(password|passphrase|db_password|db_pass)\s*=\s*['\"][a-zA-Z0-9_@#$!%^&*()-+=]{8,}['\"]"
    ),
    "Database Connection String": re.compile(
        r"(?i)(mongodb|mysql|postgresql|postgres|mssql|redis|sqlite):\/\/[a-zA-Z0-9_\-\.]+:[^@]+@[a-zA-Z0-9_\-\.]+:[0-9]+"
    ),
    "AWS Key ID / Secret": re.compile(
        r"(AKIA[0-9A-Z]{16})|(['\"][a-zA-Z0-9+/]{40}['\"])"
    ),
    "Generic Private Key": re.compile(
        r"-----BEGIN [A-Z]+ PRIVATE KEY-----"
    )
}

def scan_file(file_path):
    """Scan a single file for sensitive patterns."""
    violations = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                # Ignore comment lines to prevent false positives in documentation
                if line.strip().startswith("#") or line.strip().startswith("//"):
                    continue
                
                for pattern_name, pattern in SENSITIVE_PATTERNS.items():
                    matches = pattern.search(line)
                    if matches:
                        # Exclude harmless placeholder values like 'your-api-key' or environment variables
                        match_text = matches.group(0)
                        if "env" in match_text.lower() or "placeholder" in match_text.lower() or "your_" in match_text.lower():
                            continue
                        
                        violations.append({
                            "pattern": pattern_name,
                            "line": line_no,
                            "snippet": line.strip()[:100]  # truncate for display
                        })
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return violations

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"[*] Starting Antigravity Security Linter on {workspace_dir}...")
    
    violation_count = 0
    scanned_count = 0
    
    # Exclude typical system files or third-party packages if any
    exclude_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "assets"}
    exclude_files = {"lint_security.py"}  # Exclude itself to avoid self-matching the patterns definitions
    
    for root, dirs, files in os.walk(workspace_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file in exclude_files:
                continue
            
            # Check only source files (.py, .js, .env, .json, .yaml, .yml)
            if file.endswith((".py", ".js", ".env", ".json", ".yaml", ".yml", ".ini")):
                file_path = os.path.join(root, file)
                scanned_count += 1
                
                violations = scan_file(file_path)
                if violations:
                    print(f"\n[!] SECURITY VIOLATION DETECTED in: {file_path}")
                    for v in violations:
                        print(f"    - Line {v['line']} [{v['pattern']}]: {v['snippet']}")
                        violation_count += 1
                        
    print(f"\n[*] Scan complete. Scanned {scanned_count} files.")
    
    if violation_count > 0:
        print(f"[CRITICAL ERROR] Found {violation_count} security credential leaks.")
        # Throw the runtime exception as specified in Part 4.3
        raise SecurityViolationException(
            "Runtime terminated instantly: Hardcoded sensitive credentials found in agent tool scripts."
        )
    else:
        print("[+] Security Linter PASSED. No hardcoded credentials detected.")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except SecurityViolationException as e:
        print(f"\n[EXCEPTION] {e}")
        sys.exit(1)
