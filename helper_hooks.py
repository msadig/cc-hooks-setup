#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

"""
Unified Hook Helper Script for Claude Code
Merges all hook functionality into a single script while preserving utils dependencies.

Usage:
    helper_hooks.py <hook_type> [--options]
    
Hook Types:
    user_prompt_submit - User prompt logging and validation
    session_start - Session initialization and git status
    pre_tool_use - Tool use safety checks
    post_tool_use - Post-tool use processing
    pre_compact - Pre-compaction logging and backup
    stop - Session completion handling
    notification - General notifications
    subagent_stop - Subagent completion handling
"""

import argparse
import json
import os
import sys
import subprocess
import re
import shutil
import random
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Configuration
CLAUDE_PROJECT_DIR = Path(os.getenv("CLAUDE_PROJECT_DIR", default="."))

# Colors for output
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
CYAN = "\033[0;36m"
RED = "\033[0;31m"
NC = "\033[0m"  # No Color


# ============================================================================
# Common Functions
# ============================================================================

def log_to_json(log_name, data):
    """Common logging function for all hooks."""
    log_dir = CLAUDE_PROJECT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f'{log_name}.json'
    
    # Read existing log data or initialize empty list
    if log_file.exists():
        with open(log_file, 'r') as f:
            try:
                log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = []
    else:
        log_data = []
    
    # Append the new data
    log_data.append(data)
    
    # Write back to file with formatting
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_tts_script_path():
    """
    Determine which TTS script to use based on available API keys.
    Priority order: ElevenLabs > OpenAI > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent / "OLD" / "hooks"
    tts_dir = script_dir / "utils" / "tts"
    
    # Check for ElevenLabs API key (highest priority)
    if os.getenv('ELEVENLABS_API_KEY'):
        elevenlabs_script = tts_dir / "elevenlabs_tts.py"
        if elevenlabs_script.exists():
            return str(elevenlabs_script)
    
    # Check for OpenAI API key (second priority)
    if os.getenv('OPENAI_API_KEY'):
        openai_script = tts_dir / "openai_tts.py"
        if openai_script.exists():
            return str(openai_script)
    
    # Fall back to pyttsx3 (no API key required)
    pyttsx3_script = tts_dir / "pyttsx3_tts.py"
    if pyttsx3_script.exists():
        return str(pyttsx3_script)
    
    return None


def get_llm_script_path(purpose="completion"):
    """
    Determine which LLM script to use based on available API keys.
    Priority order: OpenAI > Anthropic
    """
    script_dir = Path(__file__).parent / "OLD" / "hooks"
    llm_dir = script_dir / "utils" / "llm"
    
    # Try OpenAI first (highest priority)
    if os.getenv('OPENAI_API_KEY'):
        oai_script = llm_dir / "oai.py"
        if oai_script.exists():
            return str(oai_script)
    
    # Try Anthropic second
    if os.getenv('ANTHROPIC_API_KEY'):
        anth_script = llm_dir / "anth.py"
        if anth_script.exists():
            return str(anth_script)
    
    return None


# ============================================================================
# User Prompt Submit Hook
# ============================================================================

def validate_prompt(prompt):
    """
    Validate the user prompt for security or policy violations.
    Returns tuple (is_valid, reason).
    """
    # Example validation rules (customize as needed)
    blocked_patterns = [
        # Add any patterns you want to block
        # Example: ('rm -rf /', 'Dangerous command detected'),
    ]
    
    prompt_lower = prompt.lower()
    
    for pattern, reason in blocked_patterns:
        if pattern.lower() in prompt_lower:
            return False, reason
    
    return True, None


def add_context_information():
    """Add context information to the user prompt (case-insensitive file matching)."""
    context_files = [
        "docs/RULES.md",
        "docs/MEMORY.md",
        "docs/REQUIREMENTS.md",
        ".claude/RULES.md",
        ".claude/MEMORY.md",
        ".claude/REQUIREMENTS.md",
    ]
    context_parts = []

    for file_path in context_files:
        dir_path = CLAUDE_PROJECT_DIR / Path(file_path).parent
        target_name = Path(file_path).name.lower()
        if dir_path.exists():
            # List all files in the directory and match case-insensitively
            for entry in dir_path.iterdir():
                if entry.is_file() and entry.name.lower() == target_name:
                    with open(entry, 'r') as f:
                        context_content = f.read().strip()
                        context_parts.append(f"Context from {entry.relative_to(CLAUDE_PROJECT_DIR)}:\n{context_content}")
                    break  # Only load the first match

    return "\n".join(context_parts)


def handle_user_prompt_submit(args, input_data):
    """Handle user_prompt_submit hook."""
    # Extract session_id and prompt
    session_id = input_data.get('session_id', 'unknown')
    prompt = input_data.get('prompt', '')
    
    # Log the user prompt
    log_to_json('user_prompt_submit', input_data)

    # Add context information (optional)
    if args.add_context:
        print(add_context_information())

    # Validate prompt if requested and not in log-only mode
    if args.validate and not args.log_only:
        is_valid, reason = validate_prompt(prompt)
        if not is_valid:
            # Exit code 2 blocks the prompt with error message
            print(f"Prompt blocked: {reason}", file=sys.stderr)
            sys.exit(2)
    
    # Success - prompt will be processed
    sys.exit(0)


# ============================================================================
# Session Start Hook
# ============================================================================

def get_git_status():
    """Get comprehensive git status information."""
    # if project has git repository
    if not (CLAUDE_PROJECT_DIR / ".git").exists():
        return None
    try:
        git_info = {}
        
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            timeout=5
        )
        git_info['branch'] = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        
        # Get remote tracking branch
        upstream_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if upstream_result.returncode == 0:
            git_info['upstream'] = upstream_result.stdout.strip()
            
            # Check if we're ahead/behind
            ahead_result = subprocess.run(
                ['git', 'rev-list', '--count', '@{u}..HEAD'],
                capture_output=True,
                text=True,
                timeout=5
            )
            behind_result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD..@{u}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if ahead_result.returncode == 0 and behind_result.returncode == 0:
                git_info['ahead'] = int(ahead_result.stdout.strip())
                git_info['behind'] = int(behind_result.stdout.strip())
        else:
            git_info['upstream'] = None
            git_info['ahead'] = 0
            git_info['behind'] = 0
        
        # Get detailed status
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if status_result.returncode == 0:
            status_lines = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
            
            # Count different types of changes
            staged = len([line for line in status_lines if line and line[0] in 'MADRC'])
            modified = len([line for line in status_lines if line and len(line) > 1 and line[1] == 'M'])
            untracked = len([line for line in status_lines if line and line.startswith('??')])
            
            git_info['staged'] = staged
            git_info['modified'] = modified
            git_info['untracked'] = untracked
            git_info['total_changes'] = len(status_lines)
        else:
            git_info['staged'] = 0
            git_info['modified'] = 0
            git_info['untracked'] = 0
            git_info['total_changes'] = 0
        
        # Get last commit
        commit_result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%h %s'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if commit_result.returncode == 0:
            git_info['last_commit'] = commit_result.stdout.strip()
        else:
            git_info['last_commit'] = None
        
        return git_info
    except Exception:
        return None


def get_recent_issues():
    """Get recent GitHub issues if gh CLI is available."""
    try:
        # Check if gh is available
        gh_check = subprocess.run(['which', 'gh'], capture_output=True)
        if gh_check.returncode != 0:
            return None
        
        # Get recent open issues
        result = subprocess.run(
            ['gh', 'issue', 'list', '--limit', '5', '--state', 'open'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def load_development_context(source):
    """Load relevant development context based on session source."""
    context_parts = []
    
    # Add timestamp
    context_parts.append(f"{CYAN}🏁 Session started at: {GREEN}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NC}")
    context_parts.append(f"{CYAN}\tSession source: {GREEN}{source}{NC}")

    # Add comprehensive git information
    git_info = get_git_status()
    if git_info:
        context_parts.append(f"\n{BLUE}📊 Git Repository Status:{NC}")
        
        # Branch information
        context_parts.append(f"{BLUE}   Branch: {GREEN}{git_info['branch']}{NC}")
        
        # Remote tracking info
        if git_info.get('upstream'):
            context_parts.append(f"{BLUE}   Tracking: {NC}{git_info['upstream']}")
            
            ahead = git_info.get('ahead', 0)
            behind = git_info.get('behind', 0)
            
            if ahead > 0 and behind > 0:
                context_parts.append(f"{YELLOW}   ⚠ Diverged: {ahead} ahead, {behind} behind{NC}")
            elif ahead > 0:
                context_parts.append(f"{GREEN}   ↑ Ahead by {ahead} commit(s){NC}")
            elif behind > 0:
                context_parts.append(f"{YELLOW}   ↓ Behind by {behind} commit(s){NC}")
            else:
                context_parts.append(f"{GREEN}   ✓ Up to date with remote{NC}")
        
        # Status details
        context_parts.append(f"{BLUE}   Status:{NC}")
        staged = git_info.get('staged', 0)
        modified = git_info.get('modified', 0)
        untracked = git_info.get('untracked', 0)
        
        if staged > 0:
            context_parts.append(f"     {GREEN}●{NC} Staged: {staged} file(s)")
        if modified > 0:
            context_parts.append(f"     {YELLOW}●{NC} Modified: {modified} file(s)")
        if untracked > 0:
            context_parts.append(f"     {YELLOW}●{NC} Untracked: {untracked} file(s)")
        
        if modified == 0 and untracked == 0 and staged == 0:
            context_parts.append(f"     {GREEN}✓ Working directory clean{NC}")
        
        # Last commit
        if git_info.get('last_commit'):
            context_parts.append(f"{BLUE}   Last commit: {NC}{git_info['last_commit']}")

    # Load project-specific context files if they exist
    context_files = [
        ".claude/CONTEXT.md",
        ".claude/TODO.md",
        "TODO.md",
        ".github/ISSUE_TEMPLATE.md"
    ]
    
    for file_path in context_files:
        if Path(CLAUDE_PROJECT_DIR / file_path).exists():
            try:
                with open(CLAUDE_PROJECT_DIR / file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        context_parts.append(f"{CYAN}\n--- Content from {file_path} ---{NC}")
                        context_parts.append(content[:1000])  # Limit to first 1000 chars
            except Exception:
                pass
    
    # Add recent issues if available
    issues = get_recent_issues()
    if issues:
        context_parts.append(f"{CYAN}\n--- Recent GitHub Issues ---{NC}")
        context_parts.append(issues)
    
    return "\n".join(context_parts)


def handle_session_start(args, input_data):
    """Handle session_start hook."""
    # Extract fields
    source = input_data.get('source', 'unknown')  # "startup", "resume", or "clear"
    
    # Log the session start event
    log_to_json('session_start', input_data)

    # Load development context if requested
    if args.load_context:
        context = load_development_context(source)
        if context:
            # Using JSON output to add context
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    # Announce session start if requested
    if args.announce:
        try:
            tts_script = get_tts_script_path()
            
            if tts_script:
                messages = {
                    "startup": "Claude Code session started",
                    "resume": "Resuming previous session",
                    "clear": "Starting fresh session"
                }
                message = messages.get(source, "Session started")
                
                subprocess.run(
                    ["uv", "run", tts_script, message],
                    capture_output=True,
                    timeout=10
                )
        except Exception:
            pass
    
    # Success
    sys.exit(0)


# ============================================================================
# Pre Tool Use Hook
# ============================================================================

def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    """
    # Normalize command by removing extra spaces and converting to lowercase
    normalized = ' '.join(command.lower().split())
    
    # Pattern 1: Standard rm -rf variations
    patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf, rm -fr, rm -Rf, etc.
        r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
        r'\brm\s+--recursive\s+--force',  # rm --recursive --force
        r'\brm\s+--force\s+--recursive',  # rm --force --recursive
        r'\brm\s+-r\s+.*-f',  # rm -r ... -f
        r'\brm\s+-f\s+.*-r',  # rm -f ... -r
    ]
    
    # Check for dangerous patterns
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True
    
    # Pattern 2: Check for rm with recursive flag targeting dangerous paths
    dangerous_paths = [
        r'/',           # Root directory
        r'/\*',         # Root with wildcard
        r'~',           # Home directory
        r'~/',          # Home directory path
        r'\$HOME',      # Home environment variable
        r'\.\.',        # Parent directory references
        r'\*',          # Wildcards in general rm -rf context
        r'\.',          # Current directory
        r'\.\s*$',      # Current directory at end of command
    ]
    
    if re.search(r'\brm\s+.*-[a-z]*r', normalized):  # If rm has recursive flag
        for path in dangerous_paths:
            if re.search(path, normalized):
                return True
    
    return False


def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.
    """
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if '.env' in file_path and not file_path.endswith('.env.sample'):
                return True
        
        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern to detect .env file access (but allow .env.sample)
            env_patterns = [
                r'\b\.env\b(?!\.sample)',  # .env but not .env.sample
                r'cat\s+.*\.env\b(?!\.sample)',  # cat .env
                r'echo\s+.*>\s*\.env\b(?!\.sample)',  # echo > .env
                r'touch\s+.*\.env\b(?!\.sample)',  # touch .env
                r'cp\s+.*\.env\b(?!\.sample)',  # cp .env
                r'mv\s+.*\.env\b(?!\.sample)',  # mv .env
            ]
            
            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True
    
    return False


def handle_pre_tool_use(args, input_data):
    """Handle pre_tool_use hook."""
    # Extract tool information
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    
    # Check for dangerous Bash commands
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        if is_dangerous_rm_command(command):
            # Exit code 2 blocks the tool use with error message
            print(f"⚠️  BLOCKED: Dangerous rm command detected!\nCommand: {command}\nThis could delete critical system files.", file=sys.stderr)
            sys.exit(2)
    
    # Check for .env file access
    if is_env_file_access(tool_name, tool_input):
        # Exit code 2 blocks the tool use with error message
        print(f"🔒 BLOCKED: Access to .env file detected!\nTool: {tool_name}\nThis file may contain sensitive API keys and secrets.", file=sys.stderr)
        sys.exit(2)
    
    # Log the tool use (optional)
    if args.log:
        log_to_json('pre_tool_use', input_data)
    
    # Tool use is allowed
    sys.exit(0)


# ============================================================================
# Post Tool Use Hook
# ============================================================================

def handle_post_tool_use(args, input_data):
    """Handle post_tool_use hook."""
    # Log the tool use result
    log_to_json('post_tool_use', input_data)
    
    # Success
    sys.exit(0)


# ============================================================================
# Pre Compact Hook
# ============================================================================

def backup_transcript(transcript_path, trigger):
    """
    Create a backup of the transcript file before compaction.
    """
    try:
        if Path(transcript_path).exists():
            # Create backups directory
            backup_dir = CLAUDE_PROJECT_DIR / "logs" / "transcript_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"transcript_{trigger}_{timestamp}.json"
            backup_path = backup_dir / backup_name
            
            # Copy the transcript file
            shutil.copy2(transcript_path, backup_path)
            return str(backup_path)
    except Exception:
        pass
    return None


def handle_pre_compact(args, input_data):
    """Handle pre_compact hook."""
    # Extract fields
    trigger = input_data.get('trigger', 'unknown')  # "limit" or "command"
    transcript_path = input_data.get('transcript_path', '')
    
    # Log the pre-compact event
    log_to_json('pre_compact', input_data)
    
    # Backup transcript if requested
    if args.backup and transcript_path:
        backup_path = backup_transcript(transcript_path, trigger)
        if backup_path and args.verbose:
            print(f"Transcript backed up to: {backup_path}")
    
    # Success
    sys.exit(0)


# ============================================================================
# Stop Hook
# ============================================================================

def get_completion_messages():
    """Return list of friendly completion messages."""
    return [
        "Work complete!",
        "All done!",
        "Task finished!",
        "Job complete!",
        "Ready for next task!"
    ]


def get_llm_completion_message():
    """
    Generate completion message using available LLM services.
    Priority order: OpenAI > Anthropic > fallback to random message
    """
    llm_script = get_llm_script_path()
    
    if llm_script:
        try:
            result = subprocess.run(
                ["uv", "run", llm_script, "--completion"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
    
    # Fall back to random message
    return random.choice(get_completion_messages())


def announce_completion():
    """Announce completion via TTS."""
    tts_script = get_tts_script_path()
    
    if not tts_script:
        return
    
    try:
        # Get completion message
        message = get_llm_completion_message()
        
        # Run TTS script
        subprocess.run(
            ["uv", "run", tts_script, message],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass


def handle_stop(args, input_data):
    """Handle stop hook."""
    # Log the stop event
    log_to_json('stop', input_data)
    
    # Announce completion if requested
    if args.announce:
        announce_completion()
    
    # Success
    sys.exit(0)


# ============================================================================
# Notification Hook
# ============================================================================

def announce_notification(text):
    """Announce notification via TTS."""
    tts_script = get_tts_script_path()
    
    if not tts_script:
        return
    
    try:
        subprocess.run(
            ["uv", "run", tts_script, text],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass


def handle_notification(args, input_data):
    """Handle notification hook."""
    # Extract notification text
    text = input_data.get('text', '')
    
    # Log the notification
    log_to_json('notification', input_data)
    
    # Announce notification if requested
    if args.announce and text:
        announce_notification(text)
    
    # Success
    sys.exit(0)


# ============================================================================
# Subagent Stop Hook
# ============================================================================

def announce_subagent_completion():
    """Announce subagent completion via TTS."""
    tts_script = get_tts_script_path()
    
    if not tts_script:
        return
    
    try:
        messages = [
            "Subagent finished!",
            "Subagent complete!",
            "Task delegation done!",
            "Subagent work done!"
        ]
        message = random.choice(messages)
        
        subprocess.run(
            ["uv", "run", tts_script, message],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass


def handle_subagent_stop(args, input_data):
    """Handle subagent_stop hook."""
    # Log the subagent stop event
    log_to_json('subagent_stop', input_data)
    
    # Announce completion if requested
    if args.announce:
        announce_subagent_completion()
    
    # Success
    sys.exit(0)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for unified hook script."""
    # Create main parser
    parser = argparse.ArgumentParser(description='Unified Hook Helper for Claude Code')
    
    # Add hook type as first positional argument
    parser.add_argument('hook_type', 
                       choices=['user_prompt_submit', 'session_start', 'pre_tool_use',
                               'post_tool_use', 'pre_compact', 'stop', 'notification',
                               'subagent_stop'],
                       help='Type of hook to execute')
    
    # Add common arguments
    parser.add_argument('--log', action='store_true',
                       help='Enable logging (default for most hooks)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--announce', action='store_true',
                       help='Enable TTS announcements')
    
    # Hook-specific arguments
    # user_prompt_submit
    parser.add_argument('--validate', action='store_true',
                       help='Enable prompt validation (user_prompt_submit)')
    parser.add_argument('--log-only', action='store_true',
                       help='Only log prompts, no validation (user_prompt_submit)')
    parser.add_argument('--add-context', action='store_true',
                       help='Add context information to prompt (user_prompt_submit)')
    
    # session_start
    parser.add_argument('--load-context', action='store_true',
                       help='Load development context at session start')
    
    # pre_compact
    parser.add_argument('--backup', action='store_true',
                       help='Backup transcript before compaction')
    
    args = parser.parse_args()
    
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Route to appropriate handler based on hook type
        if args.hook_type == 'user_prompt_submit':
            handle_user_prompt_submit(args, input_data)
        elif args.hook_type == 'session_start':
            handle_session_start(args, input_data)
        elif args.hook_type == 'pre_tool_use':
            handle_pre_tool_use(args, input_data)
        elif args.hook_type == 'post_tool_use':
            handle_post_tool_use(args, input_data)
        elif args.hook_type == 'pre_compact':
            handle_pre_compact(args, input_data)
        elif args.hook_type == 'stop':
            handle_stop(args, input_data)
        elif args.hook_type == 'notification':
            handle_notification(args, input_data)
        elif args.hook_type == 'subagent_stop':
            handle_subagent_stop(args, input_data)
        else:
            # This shouldn't happen due to choices constraint
            sys.exit(1)
            
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception as e:
        # Handle any other errors gracefully
        if args.verbose:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()