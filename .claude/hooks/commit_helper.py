#!/usr/bin/env python3
"""
commit_helper.py - Stop hook for auto-commit and test execution
Reads changed files and prompts Claude to test and commit them
"""
import json
import sys
import os

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')
SESSION_DIR = os.path.join(PROJECT_DIR, '.claude/session')

# Check if there are changed files
changed_files_path = os.path.join(SESSION_DIR, 'changed_files.txt')

changed_files = []
if os.path.exists(changed_files_path):
    try:
        with open(changed_files_path, 'r') as f:
            changed_files = [line.strip() for line in f if line.strip()]
    except IOError:
        # Exit normally if can't read file
        sys.exit(0)
else:
    # No changed files, exit silently
    sys.exit(0)

if changed_files:
    # Tell Claude to run tests and commit
    output = {
        "decision": "block",
        "reason": f"Session complete. Please run appropriate tests for these modified files and commit the changes: {', '.join(changed_files)}"
    }
    print(json.dumps(output))
    sys.exit(0)

# No changes to commit
sys.exit(0)