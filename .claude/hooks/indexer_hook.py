#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pyperclip",
# ]
# ///
"""
Indexer Hook Script for Claude Code Project Index
Combines all hook functionality with flag-based routing.

Usage:
  uv run indexer_hook.py --i-flag-hook       # UserPromptSubmit hook
  uv run indexer_hook.py --precompact        # PreCompact hook  
  uv run indexer_hook.py --project-index     # Main indexer
  uv run indexer_hook.py --session-start     # SessionStart hook
  uv run indexer_hook.py --stop              # Stop hook
"""

__version__ = "3.0.0"

import json
import sys
import argparse
import getpass
from pathlib import Path
from datetime import datetime

# Import shared utilities from utils subdirectory
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from utils.indexer.project_utils import (
    # Project utilities
    find_project_root,
    # Git utilities
    get_username, get_git_info,
    # File tracking utilities
    find_recent_files, format_time_ago, is_project_worth_indexing, get_index_age
)

# Only import pyperclip when needed for i_flag_hook
pyperclip = None

# ============================================================================
# HOOK FUNCTIONS
# ============================================================================

def session_start_hook():
    """SessionStart hook - check if project needs indexing and load preserved context after compaction."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
        source = input_data.get("source", "")
        
        # Find project root
        project_root = find_project_root()
        index_path = project_root / "PROJECT_INDEX.json"
        
        # Check if this session is starting after compaction
        if source == "compact":
            # Load preserved context from PreCompact hook
            preserved_context = load_preserved_context(project_root)
            if preserved_context:
                context_msg = f"""
📂 **Session Restored After Compaction**

Loading preserved context from before compaction:

{preserved_context}
"""
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": context_msg
                    }
                }
                print(json.dumps(output))
                sys.exit(0)
        
        # For non-compact starts, check if this is a project worth indexing
        if not is_project_worth_indexing(project_root):
            sys.exit(0)
        
        # Check index status for regular session starts
        suggestion = None
        
        if not index_path.exists():
            suggestion = f"""
📚 **Project Index Not Found**

This project appears to have significant code but no PROJECT_INDEX.json file.
An index would help me understand your codebase structure better.

**Suggestion**: Run `/index` to create a project index.

This will map out:
• Directory structure and purposes
• Function and class signatures
• Import dependencies and call graphs
• Documentation structure

You can also use the `-i` flag with any prompt (e.g., "explain the auth system -i") to auto-generate the index.
"""
        else:
            age_hours = get_index_age(index_path)
            if age_hours and age_hours > 24:
                suggestion = f"""
📚 **Project Index May Be Stale**

Your PROJECT_INDEX.json is {int(age_hours)} hours old.
Consider refreshing it if you've made significant changes.

**Quick refresh**: Run `/index` or use `-i` flag with your next prompt.
"""
        
        if suggestion:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": suggestion
                }
            }
            print(json.dumps(output))
        
        sys.exit(0)
        
    except Exception as e:
        print(f"Warning: SessionStart hook error: {e}", file=sys.stderr)
        sys.exit(0)

def load_preserved_context(project_root):
    """Load CONTEXT_STATE.md from PreCompact hook."""
    try:
        username = getpass.getuser()
        user_dir = project_root / f".claude-code-{username}"
        context_file = user_dir / "CONTEXT_STATE.md"
        
        if context_file.exists():
            with open(context_file, 'r') as f:
                content = f.read()
            return content
    except Exception:
        pass
    return None

def stop_hook():
    """Stop hook - regenerate index if PROJECT_INDEX.json exists."""
    try:
        try:
            input_data = json.load(sys.stdin)
        except:
            input_data = {}
        
        project_root = find_project_root()
        index_path = project_root / "PROJECT_INDEX.json"
        
        # Only regenerate if index already exists
        if not index_path.exists():
            sys.exit(0)
        
        print("🔄 Regenerating project index before session ends...", file=sys.stderr)
        
        # Run the indexer
        try:
            # Call project_index function directly instead of subprocess
            project_index()
            
            output = {
                "suppressOutput": False
            }
            print("🔄 PROJECT_INDEX.json refreshed with latest changes")
            print(json.dumps(output))
        except Exception as e:
            print(f"⚠️ Could not regenerate index: {e}", file=sys.stderr)
            
    except Exception as e:
        print(f"Warning: Hook error: {e}", file=sys.stderr)

def precompact_hook():
    """PreCompact Hook - save session context before compaction."""
    try:
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            input_data = {}
        
        trigger = input_data.get('trigger', 'manual')
        custom_instructions = input_data.get('custom_instructions', '')
        
        project_root = find_project_root()
        
        # Get username
        username = get_username()
        
        # Create user-specific directory
        user_dir = project_root / f'.claude-code-{username}'
        user_dir.mkdir(exist_ok=True)
        
        # Get git information
        branch, status = get_git_info()
        
        # Find recently modified files
        recent_files = find_recent_files(project_root)
        
        # Generate timestamp
        timestamp = datetime.now().isoformat()
        
        # Extract user prompts from current session
        user_prompts = extract_user_prompts(project_root, input_data)
        
        # Generate and write CONTEXT_STATE.md
        context_content = generate_context_state(branch, status, recent_files, timestamp, user_prompts)
        context_file = user_dir / 'CONTEXT_STATE.md'
        context_file.write_text(context_content)
        
        # Write log entry
        log_file = user_dir / 'precompact.log'
        log_entry = f"{timestamp} - Generated context for {trigger} compact\n"
        log_file.write_text(log_entry)
        
        # Output success message
        print(f"✅ PreCompact hook executed successfully")
        print(f"📁 Context saved to: {user_dir.name}/")
        print(f"📝 Preserved {len(recent_files)} recently modified files")
        if user_prompts:
            print(f"💬 Captured {len(user_prompts)} recent user prompts")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"⚠️ PreCompact hook warning: {str(e)}", file=sys.stderr)
        sys.exit(1)

def extract_user_prompts(project_root, input_data, max_prompts=5, max_prompt_length=2000):
    """Extract last N user prompts from current session."""
    user_prompts = []

    try:
        transcript_path = input_data.get('transcript_path', '')
        
        if transcript_path and Path(transcript_path).exists():
            with open(transcript_path, 'r') as f:
                lines = f.readlines()
                lines.reverse()

            for line in lines:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('role') == 'user' or entry.get('type') == 'user':
                        content = entry.get('content', '') or entry.get('text', '')
                        if content:
                            timestamp = entry.get('timestamp', '')
                            
                            if len(content) > max_prompt_length:
                                content = content[:max_prompt_length] + "..."
                            
                            user_prompts.append((content, timestamp))
                except json.JSONDecodeError:
                    continue
    
    except Exception:
        pass
    
    return user_prompts[-max_prompts:] if user_prompts else []

def generate_context_state(branch, status, recent_files, timestamp, user_prompts=None):
    """Generate the CONTEXT_STATE.md content."""
    content = f"""# 🔄 Auto-Generated Context State
*Generated by PreCompact hook at {timestamp}*

## 📍 Current Session
- **Git Branch**: `{branch}`
- **Working Directory**: `.`

## 💬 Recent User Prompts
"""    
    if user_prompts:
        content += "Last 5 prompts from current session:\n\n"
        for i, (prompt, prompt_timestamp) in enumerate(user_prompts, 1):
            prompt_display = prompt.replace('\n', ' ').strip()
            content += f"{i}. `{prompt_display}`\n"
            if prompt_timestamp:
                content += f"   _{prompt_timestamp}_\n"
    else:
        content += "_No recent prompts found in current session_\n"
    
    content += f"""

## 📊 Git Status
```
{status if status else 'No changes'}
```

## 📝 Recently Modified Files
Files changed in the last 4 hours:
"""
    
    for file_path, time_ago in recent_files[:10]:
        time_str = format_time_ago(time_ago)
        file_display = file_path.replace('/', '/')
        content += f"- `{file_display}` ({time_str})\n"
    
    content += """
## 📌 Context Notes

This file was automatically generated before compact to preserve session context.
It contains information about recent work that should be maintained after compact.

**Key files to review after compact:**
"""
    
    for file_path, _ in recent_files[:5]:
        content += f"- @{file_path}\n"
    
    content += """
---
*This file is auto-generated. It will be updated before each compact.*"""
    
    return content

def i_flag_hook():
    """UserPromptSubmit hook for -i and -ic flag detection."""
    # Import the flag hook logic
    from utils.indexer.flag_hook import main as flag_hook_main
    flag_hook_main()

def project_index():
    """Run the main project indexer."""
    # Import the project indexer
    from utils.indexer.project_indexer import main as project_indexer_main
    project_indexer_main()

# ============================================================================
# MAIN ENTRY POINT WITH FLAG ROUTING
# ============================================================================

def main():
    """Main entry point with flag-based routing."""
    parser = argparse.ArgumentParser(
        description="Indexer Hook Script for Claude Code Project Index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run indexer_hook.py --session-start    # SessionStart hook
  uv run indexer_hook.py --stop              # Stop hook  
  uv run indexer_hook.py --precompact        # PreCompact hook
  uv run indexer_hook.py --i-flag-hook       # UserPromptSubmit hook
  uv run indexer_hook.py --project-index     # Main indexer
        """
    )
    
    # Add mutually exclusive group for different hook modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--session-start', action='store_true',
                      help='Run SessionStart hook')
    group.add_argument('--stop', action='store_true',
                      help='Run Stop hook')
    group.add_argument('--precompact', action='store_true',
                      help='Run PreCompact hook')
    group.add_argument('--i-flag-hook', action='store_true',
                      help='Run UserPromptSubmit hook for -i/-ic flag detection')
    group.add_argument('--project-index', action='store_true',
                      help='Run main project indexer')
    
    parser.add_argument('--version', action='version',
                       version=f'%(prog)s {__version__}')
    
    args = parser.parse_args()
    
    # Route to appropriate function based on flags
    if args.session_start:
        session_start_hook()
    elif args.stop:
        stop_hook()
    elif args.precompact:
        precompact_hook()
    elif args.i_flag_hook:
        # Import pyperclip only when needed
        global pyperclip
        import pyperclip
        i_flag_hook()
    elif args.project_index:
        project_index()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()