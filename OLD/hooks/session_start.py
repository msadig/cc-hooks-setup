#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

CLAUDE_PROJECT_DIR = Path(os.getenv("CLAUDE_PROJECT_DIR", default="."))
# Colors for output
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
CYAN = "\033[0;36m"
RED = "\033[0;31m"
NC = "\033[0m"  # No Color

def log_session_start(input_data):
    """Log session start event to logs directory."""
    # Ensure logs directory exists
    log_dir = CLAUDE_PROJECT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'session_start.json'
    
    # Read existing log data or initialize empty list
    if log_file.exists():
        with open(log_file, 'r') as f:
            try:
                log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = []
    else:
        log_data = []
    
    # Append the entire input data
    log_data.append(input_data)
    
    # Write back to file with formatting
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)


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


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--load-context', action='store_true',
                          help='Load development context at session start')
        parser.add_argument('--announce', action='store_true',
                          help='Announce session start via TTS')
        args = parser.parse_args()
        
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Extract fields
        source = input_data.get('source', 'unknown')  # "startup", "resume", or "clear"
        
        # Log the session start event
        log_session_start(input_data)

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
                # Try to use TTS to announce session start
                script_dir = Path(__file__).parent
                tts_script = script_dir / "utils" / "tts" / "pyttsx3_tts.py"
                
                if tts_script.exists():
                    messages = {
                        "startup": "Claude Code session started",
                        "resume": "Resuming previous session",
                        "clear": "Starting fresh session"
                    }
                    message = messages.get(source, "Session started")
                    
                    subprocess.run(
                        ["uv", "run", str(tts_script), message],
                        capture_output=True,
                        timeout=10
                    )
                else:
                    print("TTS script not found.")
            except Exception:
                print("Error occurred while announcing session start.")
                pass
        
        # Success
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == '__main__':
    main()