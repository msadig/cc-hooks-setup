#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
rules_hook.py - Unified hook handler for Claude Code rule enforcement
Combines functionality of prompt_validator, plan_enforcer, and commit_helper
Uses flags to enable specific functionality and suggests agents based on triggered rules
"""
import json
import sys
import os
import argparse

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')

# Priority order for rule loading
PRIORITY_ORDER = {
    'critical': 4,
    'high': 3,
    'medium': 2,
    'low': 1
}

def detect_relevant_agents(manifest, matched_rule_names):
    """
    Detect which agents should be suggested based on matched rules
    
    Simple logic:
    1. User's prompt triggers rules (via keywords)
    2. Each agent lists which rules it handles
    3. If a triggered rule matches an agent's list, suggest that agent
    
    Example:
    - User types "test" → triggers "testing-standards" rule
    - "testing-specialist" agent lists "testing-standards" in its related_rules
    - Therefore, suggest "testing-specialist" agent
    """
    agent_suggestions = {}
    
    # Get agent definitions from manifest.json
    agent_integrations = manifest.get('metadata', {}).get('agent_integrations', {})
    
    if not agent_integrations or not matched_rule_names:
        return agent_suggestions
    
    # Check each agent to see if it handles any of the triggered rules
    for agent_name, agent_config in agent_integrations.items():
        relevant = False
        matched_related_rules = []
        
        # Check if this agent handles any of the triggered rules
        # An agent can list rules in either "related_rules" or "consolidates"
        all_agent_rules = agent_config.get('related_rules', []) + agent_config.get('consolidates', [])
        
        for rule in all_agent_rules:
            if rule in matched_rule_names:
                relevant = True
                if rule not in matched_related_rules:  # Avoid duplicates
                    matched_related_rules.append(rule)
        
        # If relevant, add to suggestions
        if relevant:
            # Simple: just track which rules triggered this agent
            agent_suggestions[agent_name] = {
                'related_rules': matched_related_rules
            }
    
    return agent_suggestions

def handle_prompt_validator(input_data):
    """
    Handle UserPromptSubmit hook - loads and injects rules based on keyword matching
    and suggests agents based on related rules
    """
    prompt = input_data.get('prompt', '').lower()
    session_id = input_data.get('session_id', 'default')
    
    # Check if manifest exists
    manifest_path = os.path.join(PROJECT_DIR, '.claude/rules/manifest.json')
    if not os.path.exists(manifest_path):
        return 0  # No manifest, exit silently
    
    # Load manifest
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0  # Invalid manifest, exit silently
    
    # Build list of rules with their info
    matched_rules = []
    always_load_rules = []
    matched_rule_names = set()  # Track all matched rule names for agent detection
    
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
                matched_rule_names.add(rule_name)  # Track for agent detection
                break
    
    # Sort by priority (highest first)
    matched_rules.sort(key=lambda x: PRIORITY_ORDER.get(x['priority'], 0), reverse=True)
    always_load_rules.sort(key=lambda x: PRIORITY_ORDER.get(x['priority'], 0), reverse=True)
    
    # Combine lists (remove duplicates, keeping matched version)
    matched_names = {r['name'] for r in matched_rules}
    final_rules = matched_rules + [r for r in always_load_rules if r['name'] not in matched_names]
    
    # Check for agent integrations
    agent_suggestions = detect_relevant_agents(manifest, matched_rule_names)
    
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
            output_lines.append(f"| {rule['name'].title()} | {rule['priority'].upper()} | {status} |")
        
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
            load_full = matched and not always_load
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
                        output_lines.append(f"### 📚 {rule['name'].title()} [PRIORITY: {priority.upper()}]")
                        output_lines.append("")
                        output_lines.append(f.read().strip())
                        output_lines.append("")
                        output_lines.append("---")
                        output_lines.append("")
                except IOError:
                    pass
        elif load_summary and summary:
            # Show summary only
            output_lines.append(f"### 📝 {rule['name'].title()} [PRIORITY: {priority.upper()}]")
            output_lines.append(f"**Summary:** {summary}")
            if file_path:
                output_lines.append(f"**Details:** See `.claude/rules/{file_path}` if needed")
            output_lines.append("")
            output_lines.append("---")
            output_lines.append("")
    
    # Add agent suggestions if any
    if agent_suggestions:
        output_lines.append("## 🤖 Recommended Agents")
        output_lines.append("")
        output_lines.append("Based on the triggered rules, consider using these specialized agents:")
        output_lines.append("")
        
        for agent_name, agent_info in agent_suggestions.items():
            output_lines.append(f"### **{agent_name}**")
            output_lines.append(f"Suggested because you mentioned: {', '.join(agent_info['related_rules'])}")
            output_lines.append("")
        
        output_lines.append("💡 **Tip**: Use these agents proactively by mentioning them in your requests")
        output_lines.append("Example: 'Use the {agent_name} agent to...'")
        output_lines.append("")
        output_lines.append("---")
        output_lines.append("")
    
    # Join all output lines
    complete_output = '\n'.join(output_lines)
    
    # Print to stdout for Claude to see
    print(complete_output)
    
    # Ensure session-specific directory exists
    session_dir = os.path.join(PROJECT_DIR, '.claude/sessions', session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Save the exact same output to loaded_rules.txt
    if final_rules:
        loaded_rules_path = os.path.join(session_dir, 'loaded_rules.txt')
        try:
            with open(loaded_rules_path, 'w') as f:
                f.write(complete_output)
        except IOError:
            pass
    
    return 0

def handle_plan_enforcer(input_data):
    """
    Handle PreToolUse hook - ensures plan exists and tracks file modifications
    """
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    session_id = input_data.get('session_id', 'default')
    
    # Only check for Write/Edit operations
    if tool_name not in ['Write', 'Edit', 'MultiEdit']:
        return 0
    
    # Get session-specific directory
    session_dir = os.path.join(PROJECT_DIR, '.claude/sessions', session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Define plan-related paths
    plan_path = os.path.join(session_dir, 'current_plan.md')
    approved_flag = os.path.join(session_dir, 'plan_approved')
    
    # Get the file being written/edited
    filepath = tool_input.get('file_path', '')
    
    # Allow writing to plan-related files without checks
    if filepath in [plan_path, approved_flag]:
        return 0  # Allow operation without enforcement
    
    # For other files, check if plan exists and is approved
    if not os.path.exists(plan_path):
        print(f"No plan found. Please create a plan first by writing to {plan_path}", file=sys.stderr)
        return 2  # Block operation
    
    if not os.path.exists(approved_flag):
        print(f"Plan not approved. Please get approval first by creating {approved_flag}", file=sys.stderr)
        return 2  # Block operation
    
    # Track the file being modified
    filepath = tool_input.get('file_path', '')
    if filepath:
        changed_files_path = os.path.join(session_dir, 'changed_files.txt')
        
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
                pass
    
    return 0

def handle_commit_helper(input_data):
    """
    Handle Stop hook - prompts for testing and committing changed files
    """
    session_id = input_data.get('session_id', 'default')
    
    # Get session-specific directory
    session_dir = os.path.join(PROJECT_DIR, '.claude/sessions', session_id)
    
    # Check if there are changed files
    changed_files_path = os.path.join(session_dir, 'changed_files.txt')
    
    changed_files = []
    if os.path.exists(changed_files_path):
        try:
            with open(changed_files_path, 'r') as f:
                changed_files = [line.strip() for line in f if line.strip()]
        except IOError:
            return 0
    else:
        return 0  # No changed files
    
    if changed_files:
        # Tell Claude to run tests and commit
        output = {
            "decision": "block",
            "reason": f"Session complete. Please run appropriate tests for these modified files and commit the changes: {', '.join(changed_files)}"
        }
        print(json.dumps(output))
    
    return 0

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Unified hook handler for Claude Code')
    parser.add_argument('--prompt-validator', action='store_true', 
                       help='Enable prompt validation and rule injection')
    parser.add_argument('--plan-enforcer', action='store_true',
                       help='Enable plan enforcement for file modifications')
    parser.add_argument('--commit-helper', action='store_true',
                       help='Enable commit helper for changed files')
    args = parser.parse_args()
    
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        # Exit silently on invalid input
        sys.exit(0)
    
    # Determine which hook event we're handling
    hook_event_name = input_data.get('hook_event_name', '')
    
    # Route to appropriate handler based on event and flags
    exit_code = 0
    
    if hook_event_name == 'UserPromptSubmit' and args.prompt_validator:
        exit_code = handle_prompt_validator(input_data)
    elif hook_event_name == 'PreToolUse' and args.plan_enforcer:
        exit_code = handle_plan_enforcer(input_data)
    elif hook_event_name == 'Stop' and args.commit_helper:
        exit_code = handle_commit_helper(input_data)
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()