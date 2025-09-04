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
import argparse
import datetime
import fnmatch
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')

# Priority order for rule loading
PRIORITY_ORDER = {
    'critical': 4,
    'high': 3,
    'medium': 2,
    'low': 1
}

def add_always_load_context():
    """Load critical context files that should always be available."""
    # Primary context files (glob pattern matching)
    primary_context_patterns = [
        "docs/**/RULES.md",
        "docs/**/MEMORY.md", 
        "docs/**/REQUIREMENTS.md",
        ".claude/**/RULES.md",
        ".claude/**/MEMORY.md",
        ".claude/**/REQUIREMENTS.md",
    ]
    
    context_parts = []

    # Load primary context files with glob pattern matching
    matched_primary_files = set()  # Use set to avoid duplicates
    
    for pattern in primary_context_patterns:
        # Use glob to find all files matching the pattern
        full_pattern = os.path.join(PROJECT_DIR, pattern)
        try:
            for matched_path in glob.glob(full_pattern, recursive=True):
                if os.path.isfile(matched_path):
                    matched_primary_files.add(matched_path)
        except (OSError, ValueError):
            pass  # Skip invalid patterns
    
    # Sort files for consistent ordering
    for full_path in sorted(matched_primary_files):
        try:
            with open(full_path, 'r') as f:
                context_content = f.read().strip()
                if context_content:
                    rel_path = os.path.relpath(full_path, PROJECT_DIR)
                    context_parts.append(f"Context from {rel_path}:\n{context_content}")
        except IOError:
            pass

    return "\n".join(context_parts)

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
    
    # First, always load context files (works even without manifest)
    always_load_context = add_always_load_context()
    
    # Check if manifest exists
    manifest_path = os.path.join(PROJECT_DIR, '.claude/rules/manifest.json')
    if not os.path.exists(manifest_path):
        # No manifest, but we can still provide always-load context
        if always_load_context:
            print(always_load_context)
        return 0
    
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
    
    # Add always-load context first if it exists
    if always_load_context:
        output_lines.append(always_load_context)
        output_lines.append("")
    
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
    plan_file_name = 'current_plan.md'
    plan_path = os.path.join(session_dir, plan_file_name)
    approved_flag_file_name = 'plan_approved'
    approved_flag = os.path.join(session_dir, approved_flag_file_name)
    
    # Get the file being written/edited
    filepath = tool_input.get('file_path', '')
    
    # Allow writing to plan-related files without checks
    if any(x in filepath for x in [plan_file_name, approved_flag_file_name]):
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
    Handle Stop hook - check if files need committing, otherwise exit cleanly
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
    
    if not changed_files:
        return 0  # No files to check
    
    # Check git status for each file
    uncommitted_files = []
    
    try:
        # Get git status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd=PROJECT_DIR)
        
        if result.returncode == 0:
            # Parse git status output
            git_status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Extract files that have changes (staged, modified, or untracked)
            git_changed_files = set()
            for line in git_status_lines:
                if len(line) >= 3:
                    filepath = line[3:].strip()  # Remove status prefix
                    git_changed_files.add(filepath)
            
            
            # Check if any files from changed_files.txt are uncommitted
            for filepath in changed_files:
                # Normalize paths - handle both absolute and relative paths
                if os.path.isabs(filepath):
                    # Convert absolute path to relative
                    try:
                        normalized_path = os.path.relpath(filepath, PROJECT_DIR)
                    except ValueError:
                        normalized_path = filepath
                else:
                    normalized_path = filepath
                
                if normalized_path in git_changed_files:
                    # Check if file is in .gitignore
                    gitignore_result = subprocess.run(['git', 'check-ignore', filepath], 
                                                    capture_output=True, cwd=PROJECT_DIR)
                    
                    if gitignore_result.returncode != 0:  # Not ignored
                        uncommitted_files.append(filepath)
        
        if uncommitted_files:
            # Tell Claude to run tests and commit
            output = {
                "decision": "block",
                "reason": (
                    f"Session complete. Please run appropriate tests for these modified files and commit the changes: {', '.join(uncommitted_files)}"
                    "\n If you already committed these changes, please empty the changed files list."
                )
            }
            print(json.dumps(output))
        else:
            # All files are committed or ignored, clear the changed files list
            try:
                os.remove(changed_files_path)
            except OSError:
                pass
    
    except subprocess.SubprocessError:
        # Git command failed, fall back to original behavior
        if changed_files:
            output = {
                "decision": "allow", 
                "reason": (
                    f"Session complete. Please run appropriate tests for these modified files and commit the changes: {', '.join(changed_files)}"
                    "\n If you already committed these changes, please empty the changed files list."
                )
            }
            print(json.dumps(output))
    
    return 0

def handle_pretool_file_matcher(input_data):
    """
    Handle PreToolUse hook - loads rules based on file pattern matching
    """
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    session_id = input_data.get('session_id', 'default')
    
    # Only process tools that work with files
    if tool_name not in ['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit']:
        return 0
    
    # Extract file path from tool input
    filepath = tool_input.get('file_path', '')
    if not filepath:
        return 0
    
    # Normalize the file path to be relative for pattern matching
    if os.path.isabs(filepath):
        try:
            filepath = os.path.relpath(filepath, PROJECT_DIR)
        except ValueError:
            # If relpath fails, use the absolute path
            pass
    
    # Check if manifest exists
    manifest_path = os.path.join(PROJECT_DIR, '.claude/rules/manifest.json')
    if not os.path.exists(manifest_path):
        return 0
    
    # Load manifest
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0
    
    # Build list of rules that match the file pattern
    matched_rules = []
    always_load_rules = []
    matched_rule_names = set()
    
    for rule_name, rule_data in manifest.get('rules', {}).items():
        priority = rule_data.get('priority', 'low')
        always_load_summary = rule_data.get('always_load_summary', False)
        file_matchers = rule_data.get('file_matchers', [])
        
        # Check if rule should always load summary
        if always_load_summary:
            always_load_rules.append({
                'name': rule_name,
                'data': rule_data,
                'priority': priority,
                'matched': False
            })
        
        # Check if file matches any pattern
        file_matched = False
        for pattern in file_matchers:
            # Handle both glob patterns and simple patterns
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(os.path.basename(filepath), pattern):
                file_matched = True
                break
        
        if file_matched:
            matched_rules.append({
                'name': rule_name,
                'data': rule_data,
                'priority': priority,
                'matched': True
            })
            matched_rule_names.add(rule_name)
    
    # If no rules matched, return early
    if not matched_rules and not always_load_rules:
        return 0
    
    # Sort by priority (highest first)
    matched_rules.sort(key=lambda x: PRIORITY_ORDER.get(x['priority'], 0), reverse=True)
    always_load_rules.sort(key=lambda x: PRIORITY_ORDER.get(x['priority'], 0), reverse=True)
    
    # Combine lists (remove duplicates, keeping matched version)
    matched_names = {r['name'] for r in matched_rules}
    final_rules = matched_rules + [r for r in always_load_rules if r['name'] not in matched_names]
    
    if not final_rules:
        return 0
    
    # Build output to provide as additional context
    output_lines = []
    output_lines.append(f"## Rules for: {filepath}")
    output_lines.append("")
    
    # Group rules by priority using defaultdict
    priority_groups = defaultdict(list)
    for rule in final_rules:
        priority = rule['data'].get('priority', 'low').upper()
        priority_groups[priority].append(rule)
    
    # Output rules grouped by priority (highest first)
    priority_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    for priority in priority_order:
        if priority in priority_groups:
            output_lines.append(f"### {priority}")
            for rule in priority_groups[priority]:
                rule_name = rule['name'].replace('-', ' ').title()
                summary = rule['data'].get('summary', '')
                file_ref = rule['data'].get('file', '')
                
                # Build the rule line with summary
                if summary:
                    rule_line = f"• {rule_name} - {summary}"
                else:
                    rule_line = f"• {rule_name}"
                
                # Add file reference if available
                if file_ref:
                    rule_line += f" [@.claude/rules/{file_ref}]"
                
                output_lines.append(rule_line)
            output_lines.append("")
    
    # Add footer hint for Claude
    output_lines.append("💡 Reference [@filename] to see full rule details when needed")
    
    # Join output
    complete_output = '\n'.join(output_lines)
    
    # Return as JSON with additional context that Claude will see
    if complete_output.strip():
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": complete_output
            }
        }
        print(json.dumps(output))
    
    return 0

def handle_session_start(input_data):
    """
    Handle SessionStart hook - provides development context and project overview
    """
    source = input_data.get('source', 'unknown')  # "startup", "resume", "clear"
    session_id = input_data.get('session_id', 'default')
    
    # Build development context
    context_parts = []
    
    # Add session start header
    context_parts.append(f"🏁 Session started at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    context_parts.append(f"Session source: {source}, Session ID: {session_id}")
    context_parts.append("")

    # Project-specific context files (glob pattern matching)
    context_file_patterns = [
        ".claude/**/CONTEXT.md",
        ".claude/**/WORKFLOW.md", 
        ".claude/**/SESSION.md",
        ".claude/**/*-WORKFLOW.md",
        ".claude/**/*-CONTEXT.md",
    ]
    
    # Load project-specific context files with glob pattern matching
    matched_files = set()  # Use set to avoid duplicates
    
    for pattern in context_file_patterns:
        # Use glob to find all files matching the pattern
        full_pattern = os.path.join(PROJECT_DIR, pattern)
        try:
            for matched_path in glob.glob(full_pattern, recursive=True):
                if os.path.isfile(matched_path):
                    matched_files.add(matched_path)
        except (OSError, ValueError):
            pass  # Skip invalid patterns
    
    # Sort files for consistent ordering
    for full_path in sorted(matched_files):
        try:
            with open(full_path, 'r') as f:
                content = f.read().strip()
                if content:
                    # Get relative path for display
                    rel_path = os.path.relpath(full_path, PROJECT_DIR)
                    # Limit to first 3000 chars as in original helper
                    context_parts.append(f"\n--- Content from {rel_path} ---")
                    context_parts.append(content[:3000])
        except IOError:
            pass

    # Join all context
    complete_context = "\n".join(context_parts)
    
    # Output using JSON format for SessionStart
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": complete_context
        }
    }
    print(json.dumps(output))
    
    # Log the session start event
    session_dir = os.path.join(PROJECT_DIR, '.claude/sessions', session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    try:
        log_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
            "source": source,
            "context_loaded": bool(complete_context.strip())
        }
        
        log_dir = os.path.join(PROJECT_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'session_start.json')
        
        # Read existing log data or initialize empty list
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                try:
                    log_entries = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_entries = []
        else:
            log_entries = []
        
        # Append new entry and save
        log_entries.append(log_data)
        with open(log_file, 'w') as f:
            json.dump(log_entries, f, indent=2)
    except Exception:
        pass  # Skip logging if it fails
    
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
    parser.add_argument('--session-start', action='store_true',
                       help='Enable session start context loading')
    parser.add_argument('--file-matcher', action='store_true',
                       help='Enable file pattern-based rule loading for PreToolUse')
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
    elif hook_event_name == 'PreToolUse' and args.file_matcher:
        exit_code = handle_pretool_file_matcher(input_data)
    elif hook_event_name == 'Stop' and args.commit_helper:
        exit_code = handle_commit_helper(input_data)
    elif hook_event_name == 'SessionStart' and args.session_start:
        exit_code = handle_session_start(input_data)
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()