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
from string import Template
from typing import Dict, List

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')
MANIFEST_PATH = os.path.join(PROJECT_DIR, '.claude/rules/manifest.json')

# Priority order for rule loading
PRIORITY_ORDER = {
    'critical': 4,
    'high': 3,
    'medium': 2,
    'low': 1
}
DEFAULT_TRIGGER_WORDS = ['plan approved', 'go ahead', 'proceed', 'lgtm']


def check_plan_approval(prompt: str, manifest: dict, session_id: str) -> bool:
    """
    Check if user prompt contains plan approval trigger words
    and create plan_approved file if found
    """
    # Get plan approval config
    plan_config = manifest.get('metadata', {}).get('plan_approval', {})
    
    # Get trigger words with fallback to default
    trigger_words = plan_config.get('trigger_words', DEFAULT_TRIGGER_WORDS)

    # Check if any trigger word is in prompt
    prompt_lower = prompt.lower()
    for trigger in trigger_words:
        if trigger.lower() in prompt_lower:
            # Create plan_approved file
            session_dir = os.path.join(PROJECT_DIR, '.claude/sessions', session_id)
            os.makedirs(session_dir, exist_ok=True)
            approved_flag = os.path.join(session_dir, 'plan_approved')
            
            # Create the file with timestamp
            with open(approved_flag, 'w') as f:
                f.write(f"Plan approved at: {datetime.datetime.now()}\n")
                f.write(f"Trigger word: {trigger}\n")
                f.write(f"User prompt: {prompt[:200]}...\n" if len(prompt) > 200 else f"User prompt: {prompt}\n")
            
            return True
    
    return False


def add_always_load_context(input_data: dict = None) -> str:
    """Load critical context files that should always be available."""
    session_id = input_data.get('session_id', 'default') if input_data else 'default'
    # Primary context files (glob pattern matching)
    primary_context_patterns = [
        "docs/**/RULES.md",
        "docs/**/MEMORY.md", 
        "docs/**/REQUIREMENTS.md",
        ".claude/**/RULES.md",
        ".claude/**/MEMORY.md",
        ".claude/**/REQUIREMENTS.md",
    ]

    variables = {
        'session_id': session_id,
        'timestamp': datetime.datetime.now().isoformat(),
        'timestamp_formatted': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'project_dir': PROJECT_DIR,
    }
    
    context_parts = load_templated_content(primary_context_patterns, variables)

    return context_parts

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
    prompt = input_data.get('prompt', '')  # Keep original case for approval check
    session_id = input_data.get('session_id', 'default')
    
    # Load manifest first for approval check
    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, 'r') as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Check for plan approval triggers FIRST
    if check_plan_approval(prompt, manifest, session_id):
        # Notify that plan was approved
        print("✅ Plan approved! The plan_approved flag has been created.")
        print("AI can now proceed with implementation.")
        # Don't block - allow the approval message to go through
        return 0
    
    # Convert prompt to lowercase for rule matching
    prompt_lower = prompt.lower()
    
    # First, always load context files (works even without manifest)
    always_load_context = add_always_load_context(input_data)
    
    # Check if manifest exists for rule processing
    if not manifest:
        # No manifest, but we can still provide always-load context
        if always_load_context:
            print(always_load_context)
        return 0
    
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
            if trigger.lower() in prompt_lower:
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
    
    output_lines.append("## Project Rules")
    output_lines.append("")
    
    if final_rules:
        # Group rules by priority using defaultdict
        priority_groups = defaultdict(list)
        for rule in final_rules:
            priority = rule['priority'].upper()
            priority_groups[priority].append(rule)
        
        # Output rules grouped by priority (highest first)
        priority_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        for priority in priority_order:
            if priority in priority_groups:
                output_lines.append(f"### {priority}")
                for rule in priority_groups[priority]:
                    rule_name = rule['name'].replace('-', ' ').title()
                    rule_data = rule['data']
                    matched = rule['matched']
                    summary = rule_data.get('summary', '')
                    file_ref = rule_data.get('file', '')
                    
                    # Determine what to show based on priority and match status
                    if priority == 'CRITICAL' and matched:
                        # For critical rules that are triggered, load full content
                        if file_ref:
                            rule_path = os.path.join(PROJECT_DIR, '.claude/rules', file_ref)
                            if os.path.exists(rule_path):
                                try:
                                    with open(rule_path, 'r') as f:
                                        output_lines.append(f"#### {rule_name}")
                                        output_lines.append(f.read().strip())
                                        output_lines.append("")
                                except IOError:
                                    # Fallback to summary if can't read file
                                    if summary:
                                        output_lines.append(f"• {rule_name} - {summary} [@.claude/rules/{file_ref}]")
                            else:
                                # File doesn't exist, show summary
                                if summary:
                                    output_lines.append(f"• {rule_name} - {summary} [@.claude/rules/{file_ref}]")
                        else:
                            # No file ref, just show summary
                            if summary:
                                output_lines.append(f"• {rule_name} - {summary}")
                    else:
                        # For non-critical or non-matched rules, show summary with reference
                        if summary:
                            rule_line = f"• {rule_name} - {summary}"
                            if file_ref:
                                rule_line += f" [@.claude/rules/{file_ref}]"
                            output_lines.append(rule_line)
                        else:
                            output_lines.append(f"• {rule_name}")
                output_lines.append("")
    
    # Add agent suggestions if any  
    if agent_suggestions:
        output_lines.append("### 🤖 Suggested Agents")
        for agent_name in agent_suggestions.keys():
            output_lines.append(f"• **{agent_name}** - Use for specialized {agent_name.replace('-', ' ')}")
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
    
    # Allow writing to plan file only
    if plan_file_name in filepath:
        return 0  # Allow operation without enforcement
    
    # For other files, check if plan exists and is approved
    if not os.path.exists(plan_path):
        print(f"No plan found. Please create a plan first by writing to {plan_path}", file=sys.stderr)
        return 2  # Block operation
    
    if any([
            # Plan not approved
            not os.path.exists(approved_flag),
            # Block AI from creating/editing plan_approved file
            approved_flag_file_name in filepath,
            # Special case: if the tool is Bash and command includes 'plan_approved', block it
            tool_name == 'Bash' and approved_flag_file_name in tool_input.get('command', '').lower()
        ]):
        # Check if trigger words are configured
        trigger_hint = ""
        try:
            with open(MANIFEST_PATH, 'r') as f:
                manifest = json.load(f)
                triggers = manifest.get('metadata', {}).get('plan_approval', {}).get('trigger_words', DEFAULT_TRIGGER_WORDS)
                trigger_hint = f"\n\nTo approve, use one of these phrases: {', '.join(triggers[:3])}"
        except:
            trigger_hint = f"\n\nTo approve, say: {', '.join(DEFAULT_TRIGGER_WORDS[:3])}"

        print(f"Plan not approved. User must approve the plan first.{trigger_hint}", file=sys.stderr)
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

# Template loading function (simplified)
def load_templated_content(patterns: List[str], variables: Dict[str, str] = None) -> str:
    """
    Load and process template files matching patterns.
    Uses global PROJECT_DIR for file operations.
    
    Args:
        patterns: List of glob patterns to match files
        variables: Dictionary of variables for template substitution
        
    Returns:
        Combined templated content or empty string if no files found
    """
    if variables is None:
        variables = {}
    
    all_contents = []
    matched_files = set()
    
    # Find all matching files using glob directly (like add_always_load_context)
    for pattern in patterns:
        full_pattern = os.path.join(PROJECT_DIR, pattern)
        try:
            for path in glob.glob(full_pattern, recursive=True):
                if os.path.isfile(path):
                    matched_files.add(path)
        except (OSError, ValueError):
            pass  # Skip invalid patterns
    
    # Load and process each file
    for file_path in sorted(matched_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    # Add file-specific variable
                    vars_copy = variables.copy()
                    vars_copy['template_file'] = os.path.relpath(file_path, PROJECT_DIR)
                    
                    # Apply template substitution
                    template = Template(content)
                    processed = template.safe_substitute(vars_copy)
                    
                    rel_path = os.path.relpath(file_path, PROJECT_DIR)
                    all_contents.append(f"<!-- Context from {rel_path} -->\n{processed}")
        except IOError:
            pass
    
    return '\n\n'.join(all_contents) if all_contents else ""


def handle_stop_reminder(input_data):
    """
    Handle Stop hook - provide STOPREMINDER template context if files exist
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
    
    # Prepare variables for template substitution
    variables = {
        'session_id': session_id,
        'timestamp': datetime.datetime.now().isoformat(),
        'project_dir': PROJECT_DIR,
    }
    
    # Get git status if we have changed files
    if changed_files:
        try:
            # Get git status
            result = subprocess.run(['git', 'status', '--short'], 
                                  capture_output=True, text=True, cwd=PROJECT_DIR)
            if result.returncode == 0:
                variables['git_status'] = result.stdout.strip() or "No changes"
            else:
                variables['git_status'] = "Git status unavailable"
        except Exception:
            variables['git_status'] = "Git status unavailable"
        
        # Add changed files to variables
        variables['changed_files'] = '\n'.join(f'- {f}' for f in changed_files)
        variables['changed_files_count'] = str(len(changed_files))
        variables['changed_files_list'] = ', '.join(changed_files)
    else:
        variables['git_status'] = "No changes"
        variables['changed_files'] = 'No files tracked'
        variables['changed_files_count'] = '0'
        variables['changed_files_list'] = ''
    
    # Load STOPREMINDER templates
    patterns = [
        '.claude/**/*STOPREMINDER*.md',
        '.claude/**/*STOP_REMINDER*.md',
        '**/*STOPREMINDER*.md',
        '**/*STOP_REMINDER*.md',
    ]
    template_context = load_templated_content(patterns, variables)
    
    # If there's template context, provide it as a reminder (not blocking)
    if template_context:
        # For Stop hooks, we print to stdout with exit code 0 for non-blocking reminders
        # This will be shown in transcript mode but won't affect Claude's behavior
        print(template_context)
    elif changed_files:
        # No templates but we have changed files, clear the list
        try:
            os.remove(changed_files_path)
        except OSError:
            pass
    
    return 0

def handle_immutable_files_check(input_data):
    """
    Handle PreToolUse hook - blocks editing of immutable files based on patterns
    """
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    
    # Only check for write/edit operations
    if tool_name not in ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']:
        return 0
    
    # Extract file path from tool input
    filepath = tool_input.get('file_path', '')
    if not filepath:
        return 0
    
    # Normalize the file path to be relative for pattern matching
    original_filepath = filepath
    if os.path.isabs(filepath):
        try:
            filepath = os.path.relpath(filepath, PROJECT_DIR)
        except ValueError:
            # If relpath fails, use the absolute path
            pass
    
    # Check if manifest exists
    if not os.path.exists(MANIFEST_PATH):
        return 0
    
    # Load manifest
    try:
        with open(MANIFEST_PATH, 'r') as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0
    
    # Get immutable file patterns
    immutable_patterns = manifest.get('metadata', {}).get('immutable_files', [])
    
    if not immutable_patterns:
        return 0
    
    # Check if file matches any immutable pattern
    for pattern in immutable_patterns:
        matched = False
        
        # Handle patterns with ** for recursive directory matching
        if '**' in pattern:
            # Convert glob pattern to work with fnmatch and pathlib
            # For patterns like **/dir/* or **/.ssh/*
            if pattern.startswith('**/'):
                # Remove the **/ prefix and check if the path contains the rest
                sub_pattern = pattern[3:]  # Remove **/
                # Check if the sub-pattern matches anywhere in the path
                if '/' in sub_pattern:
                    # For patterns like .ssh/* or secrets/*
                    dir_part = sub_pattern.split('/')[0]
                    if f'/{dir_part}/' in f'/{filepath}' or filepath.startswith(f'{dir_part}/'):
                        matched = True
                else:
                    # Simple pattern after **/
                    if fnmatch.fnmatch(os.path.basename(filepath), sub_pattern):
                        matched = True
            else:
                # Other ** patterns
                import_pattern = pattern.replace('**/', '*/').replace('**', '*')
                if fnmatch.fnmatch(filepath, import_pattern):
                    matched = True
        
        # Check exact pattern match, basename match, and simple patterns
        elif (fnmatch.fnmatch(filepath, pattern) or 
              fnmatch.fnmatch(os.path.basename(filepath), pattern) or
              (pattern.endswith('/*') and filepath.startswith(pattern[:-2] + '/')) or
              (pattern.endswith('/**/*') and filepath.startswith(pattern[:-5] + '/'))):
            matched = True
        
        if matched:
            # Block the operation
            print(f"🚫 BLOCKED: File '{original_filepath}' is immutable (matches pattern '{pattern}'). This file cannot be edited.", file=sys.stderr)
            return 2  # Exit code 2 blocks the tool call
    
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
    if not os.path.exists(MANIFEST_PATH):
        return 0
    
    # Load manifest
    try:
        with open(MANIFEST_PATH, 'r') as f:
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
    
    # Prepare variables for template substitution
    variables = {
        'session_id': session_id,
        'source': source,
        'timestamp': datetime.datetime.now().isoformat(),
        'timestamp_formatted': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'project_dir': PROJECT_DIR,
    }
    
    # Add git information if available
    try:
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=PROJECT_DIR)
        if result.returncode == 0:
            variables['git_branch'] = result.stdout.strip() or "unknown"
        else:
            variables['git_branch'] = "unknown"
    except Exception:
        variables['git_branch'] = "unknown"
    
    try:
        result = subprocess.run(['git', 'status', '--short'], 
                              capture_output=True, text=True, cwd=PROJECT_DIR)
        if result.returncode == 0:
            variables['git_status'] = result.stdout.strip() or "clean"
        else:
            variables['git_status'] = "unavailable"
    except Exception:
        variables['git_status'] = "unavailable"

    # Use load_templated_content for all session context files
    context_file_patterns = [
        ".claude/**/CONTEXT.md",
        ".claude/**/WORKFLOW.md", 
        ".claude/**/SESSION.md",
        ".claude/**/*-WORKFLOW.md",
        ".claude/**/*-CONTEXT.md",
        ".claude/**/*START*.md",
    ]
    
    # Load all context using the existing template system
    templated_context = load_templated_content(context_file_patterns, variables)
    
    # Build final context with session header + templated content
    if templated_context:
        complete_context = f"""🏁 Session started at: {variables['timestamp_formatted']}
Session source: {source}, Session ID: {session_id}

{templated_context}"""
    else:
        # Fallback if no context files found
        complete_context = f"""🏁 Session started at: {variables['timestamp_formatted']}
Session source: {source}, Session ID: {session_id}
Git branch: {variables['git_branch']}
Project directory: {PROJECT_DIR}"""
    
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
    parser.add_argument('--stop-reminder', action='store_true',
                       help='Enable stop reminder templates')
    parser.add_argument('--session-start', action='store_true',
                       help='Enable session start context loading')
    parser.add_argument('--file-matcher', action='store_true',
                       help='Enable file pattern-based rule loading for PreToolUse')
    parser.add_argument('--immutable-check', action='store_true',
                       help='Enable immutable files protection for PreToolUse')
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
    elif hook_event_name == 'PreToolUse' and args.immutable_check:
        exit_code = handle_immutable_files_check(input_data)
    elif hook_event_name == 'PreToolUse' and args.plan_enforcer:
        exit_code = handle_plan_enforcer(input_data)
    elif hook_event_name == 'PreToolUse' and args.file_matcher:
        exit_code = handle_pretool_file_matcher(input_data)
    elif hook_event_name == 'Stop' and args.stop_reminder:
        exit_code = handle_stop_reminder(input_data)
    elif hook_event_name == 'SessionStart' and args.session_start:
        exit_code = handle_session_start(input_data)
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()