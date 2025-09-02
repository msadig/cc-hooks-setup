#!/usr/bin/env python3
"""
plan_enforcer.py - PreToolUse hook for plan validation and file tracking
Ensures a plan exists and is approved before allowing file modifications
Tracks all modified files for testing and commit
"""
import json
import sys
import os

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')
SESSION_DIR = os.path.join(PROJECT_DIR, '.claude/session')

# Read input from stdin
try:
    input_data = json.load(sys.stdin)
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
except (json.JSONDecodeError, IOError):
    # Exit normally on invalid input
    sys.exit(0)

# Only check for Write/Edit operations
if tool_name in ['Write', 'Edit', 'MultiEdit']:
    # Ensure session directory exists
    os.makedirs(SESSION_DIR, exist_ok=True)
    
    # Check if plan exists and is approved
    plan_path = os.path.join(SESSION_DIR, 'current_plan.md')
    approved_flag = os.path.join(SESSION_DIR, 'plan_approved')
    
    if not os.path.exists(plan_path):
        print("No plan found. Please create a plan first.", file=sys.stderr)
        sys.exit(2)  # Block operation
    
    if not os.path.exists(approved_flag):
        print("Plan not approved. Please get approval first.", file=sys.stderr)
        sys.exit(2)  # Block operation
    
    # Track the file being modified
    filepath = tool_input.get('file_path', '')
    if filepath:
        changed_files_path = os.path.join(SESSION_DIR, 'changed_files.txt')
        
        # Check if file is already tracked
        existing_files = set()
        if os.path.exists(changed_files_path):
            try:
                with open(changed_files_path, 'r') as f:
                    existing_files = set(line.strip() for line in f if line.strip())
            except IOError:
                pass
        
        # Add file if not already tracked
        if filepath not in existing_files:
            try:
                with open(changed_files_path, 'a') as f:
                    f.write(f"{filepath}\n")
            except IOError:
                # Ignore write errors
                pass

# Exit successfully
sys.exit(0)