#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Indexer Hook Installation Script (Python version)
Sets up Claude Code hooks for automatic project indexing
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Get the directory where this script is located
PROJECT_ROOT = Path(__file__).parent.absolute()
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
INDEXER_SCRIPT = HOOKS_DIR / "indexer_hook.py"
HELPER_SCRIPT = HOOKS_DIR / "helper_hooks.py"
RULES_SCRIPT = HOOKS_DIR / "rules_hook.py"
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"

# Claude Code configuration
CLAUDE_CONFIG_DIR = Path.home() / ".claude"
GLOBAL_SETTINGS_FILE = CLAUDE_CONFIG_DIR / "settings.json"

# Define hook configurations as data
INDEXER_HOOKS = [
    ("UserPromptSubmit", "--i-flag-hook", 20, ""),
    ("SessionStart", "--session-start", 5, ""),
    ("PreCompact", "--precompact", 15, ""),
    ("Stop", "--stop", 45, ""),
]

HELPER_HOOKS = [
    ("SessionStart", "session_start --load-context --announce", 10, ""),
    ("PreToolUse", "pre_tool_use", 5, ""),
    ("Stop", "stop --announce", 10, ""),
    ("Notification", "notification --announce", 5, ""),
    ("SubagentStop", "subagent_stop --announce", 5, ""),
]

RULES_HOOKS = [
    ("UserPromptSubmit", "--prompt-validator", 10, ""),
    ("PreToolUse", "--immutable-check", 5, "Write|Edit|MultiEdit|NotebookEdit"),
    ("PreToolUse", "--plan-enforcer", 5, ""),
    ("PreToolUse", "--file-matcher", 5, "Read|Write|Edit|MultiEdit|NotebookEdit"),
    ("Stop", "--commit-helper", 10, ""),
    ("SessionStart", "--session-start", 10, ""),
]


def print_status(status_type: str, message: str):
    """Unified status printing"""
    icons = {
        'success': f"{GREEN}✓{NC}",
        'error': f"{RED}❌{NC}",
        'warning': f"{YELLOW}⚠{NC}",
        'info': f"{BLUE}ℹ{NC}"
    }
    print(f"{icons.get(status_type, '')} {message}")


def check_command(cmd: str, install_hint: str) -> bool:
    """Check if command exists"""
    if shutil.which(cmd) is None:
        print_status('error', f"{cmd} is not installed")
        print(install_hint)
        return False
    print_status('success', f"{cmd} is installed")
    return True


def validate_hook_script(script: Path, name: str) -> int:
    """Validate hook script. Returns 0 for success, 1 for error, 2 for warning"""
    if not script.exists():
        print_status('error', f"{name} script not found at: {script}")
        return 1
    
    try:
        result = subprocess.run(
            ["uv", "run", str(script), "--help"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return 0
        else:
            print_status('warning', f"Could not verify {name}, but continuing")
            return 2
    except Exception:
        print_status('warning', f"Could not verify {name}, but continuing")
        return 2


def create_timestamped_backup(settings_file: Path):
    """Create timestamped backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = settings_file.with_suffix(f'.json.backup.{timestamp}')
    
    shutil.copy2(settings_file, backup_file)
    print_status('success', f"Backup created: {backup_file}")
    
    # Keep only last 3 backups
    backups = sorted(settings_file.parent.glob(f"{settings_file.stem}.json.backup.*"))
    for old_backup in backups[:-3]:
        old_backup.unlink()


def hook_exists(hook_type: str, script_path: Path, command_args: str, settings: Dict) -> bool:
    """Check if a specific hook already exists"""
    hooks_list = settings.get('hooks', {}).get(hook_type, [])
    
    # Build the full command
    full_command = f"uv run {script_path} {command_args}".strip()
    
    # Check all hooks in all groups
    for group in hooks_list:
        for hook in group.get('hooks', []):
            if hook.get('command') == full_command:
                return True
    
    return False


def add_hooks_to_settings(
    script_path: Path,
    hook_name: str,
    hooks_config: List[Tuple[str, str, int, str]],
    settings_file: Path,
    is_project_local: bool = False
) -> Tuple[int, int]:
    """Add hooks to settings with duplicate detection"""
    hooks_added = 0
    hooks_skipped = 0
    
    print(f"Installing {hook_name}...")
    
    # Load existing settings
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    else:
        settings = {}
    
    # Ensure hooks structure exists
    if 'hooks' not in settings:
        settings['hooks'] = {}
    
    # Process hooks
    for hook_type, command_args, timeout, matcher in hooks_config:
        # Check if this hook already exists
        if hook_exists(hook_type, script_path, command_args, settings):
            print(f"   • {hook_type} hook already exists, skipping")
            hooks_skipped += 1
            continue
        
        # Ensure hook type array exists
        if hook_type not in settings['hooks']:
            settings['hooks'][hook_type] = []
        
        # Build hook configuration
        hook_config = {
            "type": "command",
            "command": f"uv run {script_path} {command_args}".strip(),
            "timeout": timeout
        }
        
        # Find or create the appropriate group
        hooks_list = settings['hooks'][hook_type]
        
        # Look for existing group with same matcher
        group_found = False
        for group in hooks_list:
            if matcher:
                # Group with specific matcher
                if group.get('matcher') == matcher:
                    group['hooks'].append(hook_config)
                    group_found = True
                    break
            else:
                # Group without matcher
                if 'matcher' not in group:
                    group['hooks'].append(hook_config)
                    group_found = True
                    break
        
        # Create new group if needed
        if not group_found:
            new_group = {"hooks": [hook_config]}
            if matcher:
                new_group['matcher'] = matcher
            hooks_list.append(new_group)
        
        print(f"   ✓ Added {hook_type} hook")
        hooks_added += 1
    
    # Save settings
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    # Report results
    if hooks_added > 0:
        location = "project-local" if is_project_local else "global"
        print_status('success', f"{hook_name}: Added {hooks_added} new hooks to {location} settings")
    if hooks_skipped > 0:
        print_status('info', f"{hook_name}: Skipped {hooks_skipped} existing hooks")
    
    return hooks_added, hooks_skipped


def create_index_command():
    """Create /index command"""
    print("\nCreating /index command...")
    commands_dir = Path.home() / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    
    index_command_file = commands_dir / "index.md"
    
    index_content = f"""---
name: index
description: Create or update PROJECT_INDEX.json for the current project
---

# PROJECT_INDEX Command

This command creates or updates a PROJECT_INDEX.json file that gives Claude architectural awareness of your codebase.

## What it does

The PROJECT_INDEX creates a comprehensive map of your project including:
- Directory structure and file organization
- Function and class signatures with type annotations
- Call graphs showing what calls what
- Import dependencies
- Documentation structure
- Directory purposes

## Usage

Simply type `/index` in any project directory to create or update the index.

## About the Tool

**PROJECT_INDEX** is a community tool that helps Claude Code understand your project structure better. 

- **Purpose**: Prevents code duplication, ensures proper file placement, maintains architectural consistency
- **Philosophy**: Fork and customize for your needs - Claude can modify it instantly

## How to Use the Index

After running `/index`, you can:
1. Reference it directly: `@PROJECT_INDEX.json what functions call authenticate_user?`
2. Use with -i flag: `refactor the auth system -i`
3. Add to CLAUDE.md for auto-loading: `@PROJECT_INDEX.json`

## Implementation

When you run `/index`, Claude will:
1. Check if PROJECT_INDEX scripts are installed
2. Run the indexer script to create/update PROJECT_INDEX.json
3. Provide feedback on what was indexed
4. The index is then available as PROJECT_INDEX.json

The script to run is:
`uv run {INDEXER_SCRIPT} --project-index`

## Troubleshooting

If the index is too large for your project, ask Claude:
"The indexer creates too large an index. Please modify it to only index src/ and lib/ directories"

For other issues, the tool is designed to be customized - just describe your problem to Claude!
"""
    
    with open(index_command_file, 'w') as f:
        f.write(index_content)
    
    print_status('success', "Created /index command")


def install_index_analyzer_subagent():
    """Install index-analyzer subagent"""
    print("\nInstalling index-analyzer subagent...")
    global_agents_dir = Path.home() / ".claude" / "agents"
    global_agents_dir.mkdir(parents=True, exist_ok=True)
    
    source_agent = AGENTS_DIR / "index-analyzer.md"
    if source_agent.exists():
        shutil.copy2(source_agent, global_agents_dir / "index-analyzer.md")
        print_status('success', f"Installed index-analyzer subagent to {global_agents_dir}")
    else:
        print_status('warning', f"index-analyzer.md not found in {AGENTS_DIR}/")
        print("   The -i flag may not work properly without this subagent")


def test_installation():
    """Test installation"""
    print("\nTesting installation...")
    try:
        result = subprocess.run(
            ["uv", "run", str(INDEXER_SCRIPT), "--version"],
            capture_output=True,
            text=True
        )
        if "3.0.0" in result.stdout:
            print_status('success', "Installation test passed")
        else:
            print_status('warning', "Version check failed, but installation completed")
            print("   You can still use the hooks normally")
    except Exception:
        print_status('warning', "Version check failed, but installation completed")
        print("   You can still use the hooks normally")


def prompt_yes_no(question: str) -> bool:
    """Prompt user for yes/no answer"""
    while True:
        response = input(f"{question} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def prompt_project_path() -> Optional[Path]:
    """Prompt user for project path in interactive mode"""
    print(f"   {YELLOW}Target Project Path (leave empty for current project):{NC}")
    response = input("   Path: ").strip()
    
    if not response:
        return None  # Use current project
    
    target = Path(response).expanduser().absolute()
    if not target.exists():
        print_status('error', f"Path does not exist: {target}")
        return prompt_project_path()  # Ask again
    if not target.is_dir():
        print_status('error', f"Path must be a directory: {target}")
        return prompt_project_path()  # Ask again
    
    return target


def copy_rules_hook_to_project(target_project: Path) -> Path:
    """Copy rules_hook.py to target project's .claude/hooks/"""
    target_hooks_dir = target_project / '.claude' / 'hooks'
    target_hooks_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy rules_hook.py
    source_script = RULES_SCRIPT
    target_script = target_hooks_dir / 'rules_hook.py'
    shutil.copy2(source_script, target_script)
    
    # Make executable
    import stat
    target_script.chmod(target_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    return target_script


def get_project_settings_file(target_project: Optional[Path] = None) -> Path:
    """Get the project-local settings file path"""
    if target_project:
        return target_project / '.claude' / 'settings.json'
    
    # Check if we're in a git repo or have a clear project directory
    cwd = Path.cwd()
    
    # Look for project markers to find the project root
    project_root = cwd
    for parent in [cwd] + list(cwd.parents):
        if (parent / '.git').exists() or (parent / '.claude').exists():
            project_root = parent
            break
    
    return project_root / '.claude' / 'settings.json'


def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Install Claude Code hooks')
    parser.add_argument('--non-interactive', '-n', action='store_true',
                        help='Run in non-interactive mode (skip optional hooks)')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Install all hooks without prompting')
    parser.add_argument('--indexer-only', action='store_true',
                        help='Install only the indexer hooks')
    parser.add_argument('--project-path', '-p', type=str,
                        help='Install rules hooks to specified project path')
    args = parser.parse_args()
    
    print(f"{BLUE}=== Indexer Hook Installation ==={NC}")
    print()
    
    # Validate project path if provided via command line
    if args.project_path:
        target = Path(args.project_path).expanduser().absolute()
        if not target.exists():
            print_status('error', f"Target project does not exist: {target}")
            sys.exit(1)
        if not target.is_dir():
            print_status('error', f"Target must be a directory: {target}")
            sys.exit(1)
    
    # Check dependencies
    print("Checking dependencies...")
    if not check_command("uv", "Please install UV first:\n  curl -LsSf https://astral.sh/uv/install.sh | sh\n  or\n  brew install uv"):
        sys.exit(1)
    
    # Check for Claude Code configuration directory
    if not CLAUDE_CONFIG_DIR.exists():
        print(f"{YELLOW}Creating Claude Code config directory...{NC}")
        CLAUDE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    print_status('success', "Claude Code directory exists")
    
    # Verify project structure
    if not INDEXER_SCRIPT.exists():
        print_status('error', f"Indexer script not found at: {INDEXER_SCRIPT}")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)
    print_status('success', "Project structure verified")
    
    # Test UV can run the indexer script
    print()
    print("Testing UV execution...")
    result = validate_hook_script(INDEXER_SCRIPT, "Indexer script")
    if result == 0:
        print_status('success', "UV can execute indexer script")
    
    # Ensure global settings.json exists
    if not GLOBAL_SETTINGS_FILE.exists():
        GLOBAL_SETTINGS_FILE.write_text("{}")
    
    # Create a backup for global settings
    print()
    print("Creating backup...")
    create_timestamped_backup(GLOBAL_SETTINGS_FILE)
    
    # Install indexer hooks (always installed to global)
    print()
    print("Configuring indexer hooks...")
    add_hooks_to_settings(INDEXER_SCRIPT, "Indexer", INDEXER_HOOKS, GLOBAL_SETTINGS_FILE)
    
    # Create /index command
    create_index_command()
    
    # Install index-analyzer subagent
    install_index_analyzer_subagent()
    
    # Test installation
    test_installation()
    
    # Interactive additional hooks installation
    install_helper = False
    install_rules = False
    
    if args.indexer_only:
        print()
        print(f"{BLUE}Installing indexer hooks only (--indexer-only mode){NC}")
    elif args.non_interactive:
        print()
        print(f"{BLUE}Non-interactive mode - skipping optional hooks{NC}")
    elif args.all:
        print()
        print(f"{BLUE}Installing all hooks (--all mode){NC}")
        install_helper = True
        install_rules = True
    else:
        print()
        print(f"{BLUE}=== Additional Hooks Installation ==={NC}")
        print()
        print("Would you like to install additional hooks for enhanced functionality?")
        print("(These are optional and can be customized later)")
        print()
        
        # Helper Hooks Installation (global)
        print(f"{YELLOW}📦 Helper Hooks{NC}")
        print("   Provides:")
        print("   • Git status display on session start")
        print("   • Safety protection (rm -rf blocking)")
        print("   • Session notifications and TTS support")
        print("   • Automatic context loading")
        print()
        
        install_helper = prompt_yes_no("Install Helper Hooks?")
        
        print()
        
        # Rules Hook Installation (project-local)
        print(f"{YELLOW}📋 Rules Hook{NC}")
        print("   Provides:")
        print("   • Auto-loads project rules from .claude/rules/")
        print("   • File pattern matching for automatic rule loading")
        print("   • Enforces planning before code changes")
        print("   • Commit reminders for modified files")
        print("   • Context-aware development workflow")
        print()
        print(f"   {YELLOW}Note: Rules hooks will be installed to PROJECT-LOCAL settings{NC}")
        print(f"   {YELLOW}This keeps rules specific to this project{NC}")
        print()
        
        install_rules = prompt_yes_no("Install Rules Hook?")
        
        if install_rules and not args.project_path:
            # Ask for project path if user wants to install rules
            target_project = prompt_project_path()
            args.project_path = str(target_project) if target_project else None
    
    # Install helper hooks if requested
    if install_helper:
        result = validate_hook_script(HELPER_SCRIPT, "Helper hooks")
        if result != 1:
            add_hooks_to_settings(HELPER_SCRIPT, "Helper", HELPER_HOOKS, GLOBAL_SETTINGS_FILE)
    elif not args.indexer_only and not args.all:
        print("Skipping Helper Hooks installation")
    
    # Install rules hooks if requested
    if install_rules:
        result = validate_hook_script(RULES_SCRIPT, "Rules hook")
        if result != 1:
            # Determine target project
            if args.project_path:
                # Use provided path from command line or interactive prompt
                target_project = Path(args.project_path).expanduser().absolute()
            else:
                # Use current project
                target_project = None
            
            project_settings = get_project_settings_file(target_project)
            
            # If installing to different project, copy script first
            if target_project:
                print(f"   Copying rules hook to target project: {target_project}")
                rules_script_path = copy_rules_hook_to_project(target_project)
                print_status('success', f"Copied rules_hook.py to {rules_script_path}")
            else:
                # Use original script path for current project
                rules_script_path = RULES_SCRIPT
                print("   Installing to current project")
            
            print(f"   Settings location: {project_settings}")
            
            # Create backup if project settings exist
            if project_settings.exists():
                create_timestamped_backup(project_settings)
            
            add_hooks_to_settings(
                rules_script_path,  # Use the appropriate script path
                "Rules", 
                RULES_HOOKS, 
                project_settings,
                is_project_local=True
            )
    elif not args.indexer_only and not args.all:
        print("Skipping Rules Hook installation")
    
    # Show installed hooks summary
    print()
    print(f"{BLUE}=== Installed Hooks Summary ==={NC}")
    print()
    print(f"{GREEN}✓{NC} Indexer Hooks (Always installed to global):")
    print("   • UserPromptSubmit: Detects -i flag for index-aware mode")
    print("   • SessionStart: Auto-indexes on session start")
    print("   • PreCompact: Updates index before compacting")
    print("   • Stop: Updates index on session end")
    
    # Check what was actually installed
    if GLOBAL_SETTINGS_FILE.exists():
        with open(GLOBAL_SETTINGS_FILE, 'r') as f:
            global_settings = json.load(f)
            
        # Check if helper hooks were installed
        if any("helper_hooks.py" in str(hook.get('command', '')) 
               for group in global_settings.get('hooks', {}).get('SessionStart', [])
               for hook in group.get('hooks', [])):
            print()
            print(f"{GREEN}✓{NC} Helper Hooks (Global):")
            print("   • SessionStart: Shows git status and loads context")
            print("   • PreToolUse: Blocks dangerous commands")
            print("   • Stop: Session notifications")
            print("   • Notification: Custom notifications")
            print("   • SubagentStop: Subagent completion notifications")
    
    # Check project-local rules
    project_settings = get_project_settings_file()
    if project_settings.exists():
        with open(project_settings, 'r') as f:
            local_settings = json.load(f)
            
        if any("rules_hook.py" in str(hook.get('command', '')) 
               for groups in local_settings.get('hooks', {}).values()
               for group in groups
               for hook in group.get('hooks', [])):
            print()
            print(f"{GREEN}✓{NC} Rules Hook (Project-local):")
            print("   • UserPromptSubmit: Validates prompts against project rules")
            print("   • PreToolUse: Enforces planning and loads rules by file patterns")
            print("   • Stop: Reminds to commit changes")
            print("   • SessionStart: Loads project context")
    
    # Final instructions
    print()
    print(f"{GREEN}=== Installation Complete! ==={NC}")
    print()
    print(f"📁 Installation location: {PROJECT_ROOT}/.claude")
    print()
    print("🚀 Usage:")
    print("   • Type /index in any project to create/update the index")
    print("   • Add -i flag to any prompt for index-aware mode (e.g., 'fix auth bug -i')")
    print("     This triggers the index-analyzer subagent for deep code analysis")
    print("   • Use -ic flag to export to clipboard for large context AI models")
    print("   • Reference with @PROJECT_INDEX.json when you need architectural awareness")
    print("   • The index is created automatically when you use -i flag")
    print()
    print("📝 Manual usage:")
    print("   • Command: /index (in Claude Code)")
    print(f"   • Direct: uv run {INDEXER_SCRIPT} --project-index")
    print("   Both create PROJECT_INDEX.json in the current directory")
    print()
    print("📍 Hook installation locations:")
    print(f"   • Global hooks (indexer, helper): {GLOBAL_SETTINGS_FILE}")
    print(f"   • Project hooks (rules): {project_settings}")
    print("   • All hooks use absolute paths to this installation")
    print()
    print(f"{BLUE}Happy coding with the Indexer Hook!{NC}")


if __name__ == "__main__":
    main()