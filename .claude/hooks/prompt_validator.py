#!/usr/bin/env python3
"""
prompt_validator.py - UserPromptSubmit hook for rule injection
Loads and injects rules based on keyword matching from manifest
Implements priority-based loading and summary/full content strategy
Saves the complete context to loaded_rules.txt for debugging/auditing
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

# Build the complete output that will be shown to Claude
output_lines = []
output_lines.append("## Project Rules Loaded")
output_lines.append("")

if final_rules:
    output_lines.append("### Rule Priority Summary")
    output_lines.append("| Rule | Priority | Status |")
    output_lines.append("|------|----------|--------|")
    
    for rule in final_rules:
        status = "✅ Triggered" if rule['matched'] else "📋 Always Loaded"
        output_lines.append(f"| {rule['name']} | {rule['priority'].upper()} | {status} |")
    
    output_lines.append("")
    output_lines.append("---")
    output_lines.append("")

# Load rules based on priority and loading matrix
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
                    output_lines.append(f"### 📚 {rule['name']} [PRIORITY: {priority.upper()}]")
                    output_lines.append("")
                    output_lines.append(f.read().strip())
                    output_lines.append("")
                    output_lines.append("---")
                    output_lines.append("")
            except IOError:
                pass
    elif load_summary and summary:
        # Show summary only
        output_lines.append(f"### 📝 {rule['name']} [PRIORITY: {priority.upper()}]")
        output_lines.append(f"**Summary:** {summary}")
        if file_path:
            output_lines.append(f"**Details:** See `.claude/rules/{file_path}` if needed")
        output_lines.append("")
        output_lines.append("---")
        output_lines.append("")

# Join all output lines
complete_output = '\n'.join(output_lines)

# Print to stdout for Claude to see
print(complete_output)

# Ensure session directory exists
session_dir = os.path.join(PROJECT_DIR, '.claude/session')
os.makedirs(session_dir, exist_ok=True)

# Save the exact same output to loaded_rules.txt
if final_rules:
    loaded_rules_path = os.path.join(session_dir, 'loaded_rules.txt')
    try:
        with open(loaded_rules_path, 'w') as f:
            f.write(complete_output)
    except IOError:
        pass

# Exit successfully
sys.exit(0)