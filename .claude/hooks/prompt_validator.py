#!/usr/bin/env python3
"""
prompt_validator.py - UserPromptSubmit hook for rule injection
Loads and injects rules based on keyword matching from manifest
Implements priority-based loading and summary/full content strategy
"""
import json
import sys
import os

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')

# Priority order (higher number = higher priority)
PRIORITY_ORDER = {
    'critical': 4,
    'high': 3,
    'medium': 2,
    'low': 1
}

# Read prompt from stdin
try:
    input_data = json.load(sys.stdin)
    prompt = input_data.get('prompt', '').lower()
except (json.JSONDecodeError, IOError):
    # Exit silently on invalid input
    sys.exit(0)

# Check if manifest exists
manifest_path = os.path.join(PROJECT_DIR, '.claude/rules/manifest.json')
if not os.path.exists(manifest_path):
    # No manifest, exit silently
    sys.exit(0)

# Load manifest
try:
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
except (json.JSONDecodeError, IOError):
    # Invalid manifest, exit silently
    sys.exit(0)

# Build list of rules with their info
matched_rules = []
always_load_rules = []

for rule_name, rule_data in manifest.get('rules', {}).items():
    priority = rule_data.get('priority', 'low')
    always_load_summary = rule_data.get('always_load_summary', False)
    
    # Check if rule should always load summary
    if always_load_summary:
        always_load_rules.append({
            'name': rule_name,
            'data': rule_data,
            'priority': priority,
            'matched': False
        })
    
    # Check if any trigger keyword is in prompt
    for trigger in rule_data.get('triggers', []):
        if trigger.lower() in prompt:
            matched_rules.append({
                'name': rule_name,
                'data': rule_data,
                'priority': priority,
                'matched': True
            })
            break

# Sort by priority (highest first)
matched_rules.sort(key=lambda x: PRIORITY_ORDER.get(x['priority'], 0), reverse=True)
always_load_rules.sort(key=lambda x: PRIORITY_ORDER.get(x['priority'], 0), reverse=True)

# Combine lists (remove duplicates, keeping matched version)
matched_names = {r['name'] for r in matched_rules}
final_rules = matched_rules + [r for r in always_load_rules if r['name'] not in matched_names]

# Output rules based on loading matrix
print("## Project Rules Loaded\n")

if final_rules:
    print("### Rule Priority Summary")
    print("| Rule | Priority | Status |")
    print("|------|----------|--------|")
    
    for rule in final_rules:
        status = "✅ Triggered" if rule['matched'] else "📋 Always Loaded"
        print(f"| {rule['name']} | {rule['priority'].upper()} | {status} |")
    
    print("\n---\n")

# Load rules based on priority and loading matrix
loaded_files = []
for rule in final_rules:
    rule_data = rule['data']
    priority = rule['priority']
    matched = rule['matched']
    always_load = rule_data.get('always_load_summary', False)
    summary = rule_data.get('summary', '')
    file_path = rule_data.get('file', '')
    
    # Determine what to load based on matrix
    load_full = False
    load_summary = False
    
    if priority == 'critical':
        # Critical: always show at least summary, full if triggered
        load_summary = True
        load_full = matched or always_load
    elif priority == 'high':
        # High: show summary if triggered or always_load
        load_summary = matched or always_load
        load_full = matched and not always_load  # Only full if matched and not always_load
    elif priority == 'medium':
        # Medium: summary only when triggered
        load_summary = matched
    else:  # low
        # Low: reference only when triggered
        load_summary = matched
    
    # Output based on decision
    if load_full and file_path:
        # Load full content
        rule_path = os.path.join(PROJECT_DIR, '.claude/rules', file_path)
        if os.path.exists(rule_path):
            try:
                with open(rule_path, 'r') as f:
                    print(f"### 📚 {rule['name']} [PRIORITY: {priority.upper()}]\n")
                    print(f.read())
                    print("\n---\n")
                    loaded_files.append(file_path)
            except IOError:
                pass
    elif load_summary and summary:
        # Show summary only
        print(f"### 📝 {rule['name']} [PRIORITY: {priority.upper()}]")
        print(f"**Summary:** {summary}")
        if file_path:
            print(f"**Details:** See `.claude/rules/{file_path}` if needed")
        print("\n---\n")

# Ensure session directory exists
session_dir = os.path.join(PROJECT_DIR, '.claude/session')
os.makedirs(session_dir, exist_ok=True)

# Save loaded rules list
if loaded_files:
    loaded_rules_path = os.path.join(session_dir, 'loaded_rules.txt')
    try:
        with open(loaded_rules_path, 'w') as f:
            f.write('\n'.join(loaded_files))
    except IOError:
        pass

# Exit successfully
sys.exit(0)