#!/usr/bin/env python3
"""
Test script for immutable files feature
"""
import json
import subprocess
import sys
import os
import tempfile
from pathlib import Path

# Test colors
GREEN = '\033[32m'
RED = '\033[31m'
YELLOW = '\033[33m'
CYAN = '\033[36m'
NC = '\033[0m'  # No Color

def print_test(test_name, passed, message=""):
    """Print test result with color"""
    if passed:
        print(f"{GREEN}✓{NC} {test_name}")
    else:
        print(f"{RED}✗{NC} {test_name}")
        if message:
            print(f"  {message}")

def run_hook_test(hook_path, tool_name, file_path, session_id="test-session"):
    """Test the hook with given parameters"""
    input_data = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {
            "file_path": file_path
        },
        "session_id": session_id,
        "transcript_path": "/tmp/test.jsonl",
        "cwd": os.getcwd()
    }
    
    # Run the hook
    try:
        result = subprocess.run(
            ["uv", "run", hook_path, "--immutable-check"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def main():
    print(f"\n{CYAN}=== Testing Immutable Files Feature ==={NC}\n")
    
    # Path to the hook script
    hook_path = ".claude/hooks/rules_hook.py"
    
    if not os.path.exists(hook_path):
        print(f"{RED}Error: Hook script not found at {hook_path}{NC}")
        sys.exit(1)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test patterns that should be blocked
    blocked_patterns = [
        (".env", "Environment file"),
        (".env.local", "Local environment file"),
        ("production.env", "Production environment file"),
        (".git/config", "Git configuration"),
        (".git/HEAD", "Git HEAD file"),
        ("private.key", "Private key file"),
        ("certificate.pem", "Certificate file"),
        ("server.crt", "Server certificate"),
        (".ssh/id_rsa", "SSH private key"),
        ("secrets/api_key.txt", "Secrets directory file"),
        ("credentials/password.txt", "Credentials file"),
        ("token.secret", "Secret token file"),
        ("private/data.json", "Private directory file"),
        (".claude/rules/manifest.json", "Manifest file itself")
    ]
    
    # Test patterns that should NOT be blocked
    allowed_patterns = [
        ("main.py", "Regular Python file"),
        ("src/app.js", "Regular JavaScript file"),
        ("README.md", "Documentation file"),
        ("package.json", "Package file"),
        ("test.txt", "Regular text file"),
        ("environment.py", "File with 'env' in name but not .env"),
        ("gitignore", "File starting with git but not in .git"),
        ("public/index.html", "Public directory file")
    ]
    
    # Test Write operations (should be blocked for immutable files)
    print(f"{YELLOW}Testing WRITE operations on immutable files:{NC}")
    for file_pattern, description in blocked_patterns:
        returncode, stdout, stderr = run_hook_test(hook_path, "Write", file_pattern)
        passed = returncode == 2  # Should return 2 (blocked)
        print_test(f"Block Write to {file_pattern} ({description})", passed, 
                  f"Got return code {returncode}, expected 2")
        if passed:
            tests_passed += 1
        else:
            tests_failed += 1
    
    print(f"\n{YELLOW}Testing WRITE operations on allowed files:{NC}")
    for file_pattern, description in allowed_patterns:
        returncode, stdout, stderr = run_hook_test(hook_path, "Write", file_pattern)
        passed = returncode == 0  # Should return 0 (allowed)
        print_test(f"Allow Write to {file_pattern} ({description})", passed,
                  f"Got return code {returncode}, expected 0")
        if passed:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test Edit operations (should be blocked for immutable files)
    print(f"\n{YELLOW}Testing EDIT operations on immutable files:{NC}")
    sample_blocked = [blocked_patterns[0], blocked_patterns[3], blocked_patterns[6]]
    for file_pattern, description in sample_blocked:
        returncode, stdout, stderr = run_hook_test(hook_path, "Edit", file_pattern)
        passed = returncode == 2  # Should return 2 (blocked)
        print_test(f"Block Edit to {file_pattern} ({description})", passed,
                  f"Got return code {returncode}, expected 2")
        if passed:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test Read operations (should NOT be blocked)
    print(f"\n{YELLOW}Testing READ operations (should always be allowed):{NC}")
    sample_files = [blocked_patterns[0], blocked_patterns[3], allowed_patterns[0]]
    for file_pattern, description in sample_files:
        returncode, stdout, stderr = run_hook_test(hook_path, "Read", file_pattern[0])
        passed = returncode == 0  # Should return 0 (allowed - Read is not blocked)
        print_test(f"Allow Read of {file_pattern[0]} ({description})", passed,
                  f"Got return code {returncode}, expected 0")
        if passed:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test absolute paths
    print(f"\n{YELLOW}Testing absolute paths:{NC}")
    abs_path_tests = [
        (f"{os.getcwd()}/.env", "Absolute path to .env"),
        (f"{os.getcwd()}/private.key", "Absolute path to private.key"),
        (f"{os.getcwd()}/src/app.js", "Absolute path to allowed file")
    ]
    
    for file_path, description in abs_path_tests:
        returncode, stdout, stderr = run_hook_test(hook_path, "Write", file_path)
        # First two should be blocked, last one allowed
        expected = 2 if ".env" in file_path or "private.key" in file_path else 0
        passed = returncode == expected
        print_test(f"{'Block' if expected == 2 else 'Allow'} {description}", passed,
                  f"Got return code {returncode}, expected {expected}")
        if passed:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Summary
    print(f"\n{CYAN}=== Test Summary ==={NC}")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"{GREEN}Passed: {tests_passed}{NC}")
    if tests_failed > 0:
        print(f"{RED}Failed: {tests_failed}{NC}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}✨ All tests passed! The immutable files feature is working correctly.{NC}")

if __name__ == "__main__":
    main()