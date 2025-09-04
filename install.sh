#!/bin/bash

# Indexer Hook Installation Script
# Sets up Claude Code hooks for automatic project indexing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"
INDEXER_SCRIPT="$HOOKS_DIR/indexer_hook.py"
HELPER_SCRIPT="$HOOKS_DIR/helper_hooks.py"
RULES_SCRIPT="$HOOKS_DIR/rules_hook.py"
AGENTS_DIR="$PROJECT_ROOT/.claude/agents"

# Claude Code configuration
CLAUDE_CONFIG_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_CONFIG_DIR/settings.json"

# Define hook configurations as data
INDEXER_HOOKS=(
    "UserPromptSubmit" "--i-flag-hook" 20
    "SessionStart" "--session-start" 5
    "PreCompact" "--precompact" 15
    "Stop" "--stop" 45
)

HELPER_HOOKS=(
    "SessionStart" "session_start --load-context --announce" 10
    "PreToolUse" "pre_tool_use" 5
    "Stop" "stop --announce" 10
    "Notification" "notification --announce" 5
    "SubagentStop" "subagent_stop --announce" 5
)

RULES_HOOKS=(
    "UserPromptSubmit" "--prompt-validator" 10
    "PreToolUse" "--immutable-check" 5
    "PreToolUse" "--plan-enforcer" 5
    "PreToolUse" "--file-matcher" 5
    "Stop" "--commit-helper" 10
    "SessionStart" "--session-start" 10
)

# ==================== Helper Functions ====================

# Unified status printing
print_status() {
    local type=$1
    local message=$2
    case $type in
        success) echo -e "${GREEN}✓${NC} $message" ;;
        error)   echo -e "${RED}❌${NC} $message" ;;
        warning) echo -e "${YELLOW}⚠${NC} $message" ;;
        info)    echo -e "${BLUE}ℹ${NC} $message" ;;
    esac
}

# Check if command exists
require_command() {
    local cmd=$1
    local install_hint=$2
    
    if ! command -v "$cmd" &> /dev/null; then
        print_status error "$cmd is not installed"
        echo "$install_hint"
        exit 1
    fi
    print_status success "$cmd is installed"
}

# Validate hook script
validate_hook_script() {
    local script=$1
    local name=$2
    
    if [ ! -f "$script" ]; then
        print_status error "$name script not found at: $script"
        return 1
    fi
    
    if uv run "$script" --help &> /dev/null; then
        return 0
    else
        print_status warning "Could not verify $name, but continuing"
        return 2
    fi
}

# Create timestamped backup
create_timestamped_backup() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="${SETTINGS_FILE}.backup.${timestamp}"
    
    cp "$SETTINGS_FILE" "$backup_file"
    print_status success "Backup created: $backup_file"
    
    # Keep only last 3 backups
    ls -t "${SETTINGS_FILE}.backup."* 2>/dev/null | tail -n +4 | xargs -r rm
}

# Check if a specific hook already exists
hook_exists() {
    local hook_type=$1
    local script_path=$2
    local command_args=$3
    
    # Check if settings file exists
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        echo "false"
        return
    fi
    
    # Updated to handle grouped structure - checks all hooks in all groups
    jq --arg type "$hook_type" \
       --arg cmd "uv run $script_path $command_args" \
       '
       .hooks[$type] // [] |
       # Flatten all hooks from all groups
       map(.hooks[]?) |
       # Check if any hook matches the command
       any(.command == $cmd)
       ' "$SETTINGS_FILE"
}

# Add hooks to settings with duplicate detection
add_hooks_to_settings() {
    local script_path=$1
    local hook_name=$2
    shift 2
    
    local hooks_added=0
    local hooks_skipped=0
    
    echo "Installing $hook_name..."
    
    # Process hooks in groups of 3 (type, args, timeout)
    while [ $# -gt 0 ]; do
        local hook_type=$1
        local command_args=$2
        local timeout=$3
        shift 3
        
        # Check if this hook already exists
        if [[ $(hook_exists "$hook_type" "$script_path" "$command_args") == "true" ]]; then
            echo "   • $hook_type hook already exists, skipping"
            ((hooks_skipped++))
            continue
        fi
        
        # Add the hook to existing group or create new one
        jq --arg type "$hook_type" \
           --arg cmd "uv run $script_path $command_args" \
           --argjson timeout "$timeout" \
           '
           # Initialize hooks object and type array if needed
           if .hooks == null then .hooks = {} else . end |
           if .hooks[$type] == null then .hooks[$type] = [] else . end |
           
           # Find index of first group without matcher - for hooks that do not use matchers
           (.hooks[$type] | to_entries | map(select(.value | has("matcher") | not)) | first // null | .key // null) as $group_index |
           
           if $group_index != null then
               # Append to existing group without matcher
               .hooks[$type][$group_index].hooks += [{
                   "type": "command",
                   "command": $cmd,
                   "timeout": $timeout
               }]
           else
               # Create new group without matcher
               .hooks[$type] += [{
                   "hooks": [{
                       "type": "command",
                       "command": $cmd,
                       "timeout": $timeout
                   }]
               }]
           end
           ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && \
        mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
        
        echo "   ✓ Added $hook_type hook"
        ((hooks_added++))
    done
    
    # Report results
    if [ $hooks_added -gt 0 ]; then
        print_status success "$hook_name: Added $hooks_added new hooks"
    fi
    if [ $hooks_skipped -gt 0 ]; then
        print_status info "$hook_name: Skipped $hooks_skipped existing hooks"
    fi
    
    return 0
}

# ==================== Main Installation ====================

echo -e "${BLUE}=== Indexer Hook Installation ===${NC}"
echo

# Check dependencies
echo "Checking dependencies..."
require_command "uv" "Please install UV first:
  curl -LsSf https://astral.sh/uv/install.sh | sh
  or
  brew install uv"

require_command "jq" "Please install jq first:
  brew install jq  # on macOS
  apt-get install jq  # on Ubuntu/Debian"

# Check for Claude Code configuration directory
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating Claude Code config directory...${NC}"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi
print_status success "Claude Code directory exists"

# Verify project structure
if [ ! -f "$INDEXER_SCRIPT" ]; then
    print_status error "Indexer script not found at: $INDEXER_SCRIPT"
    echo "Make sure you're running this from the project root directory"
    exit 1
fi
print_status success "Project structure verified"

# Test UV can run the indexer script
echo
echo "Testing UV execution..."
if uv run "$INDEXER_SCRIPT" --help &> /dev/null; then
    print_status success "UV can execute indexer script"
else
    print_status warning "UV test failed, but hooks may still work"
fi

# Ensure settings.json exists
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "{}" > "$SETTINGS_FILE"
fi

# Create a backup
echo
echo "Creating backup..."
create_timestamped_backup

# Install indexer hooks (always installed)
echo
echo "Configuring indexer hooks..."
add_hooks_to_settings "$INDEXER_SCRIPT" "Indexer" "${INDEXER_HOOKS[@]}"

# Create /index command
echo
echo "Creating /index command..."
mkdir -p "$HOME/.claude/commands"
cat > "$HOME/.claude/commands/index.md" << EOF
---
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

Simply type \`/index\` in any project directory to create or update the index.

## About the Tool

**PROJECT_INDEX** is a community tool that helps Claude Code understand your project structure better. 

- **Purpose**: Prevents code duplication, ensures proper file placement, maintains architectural consistency
- **Philosophy**: Fork and customize for your needs - Claude can modify it instantly

## How to Use the Index

After running \`/index\`, you can:
1. Reference it directly: \`@PROJECT_INDEX.json what functions call authenticate_user?\`
2. Use with -i flag: \`refactor the auth system -i\`
3. Add to CLAUDE.md for auto-loading: \`@PROJECT_INDEX.json\`

## Implementation

When you run \`/index\`, Claude will:
1. Check if PROJECT_INDEX scripts are installed
2. Run the indexer script to create/update PROJECT_INDEX.json
3. Provide feedback on what was indexed
4. The index is then available as PROJECT_INDEX.json

The script to run is:
\`uv run $INDEXER_SCRIPT --project-index\`

## Troubleshooting

If the index is too large for your project, ask Claude:
"The indexer creates too large an index. Please modify it to only index src/ and lib/ directories"

For other issues, the tool is designed to be customized - just describe your problem to Claude!
EOF

print_status success "Created /index command"

# Install index-analyzer subagent
echo
echo "Installing index-analyzer subagent..."
GLOBAL_AGENTS_DIR="$HOME/.claude/agents"
mkdir -p "$GLOBAL_AGENTS_DIR"

if [ -f "$AGENTS_DIR/index-analyzer.md" ]; then
    cp "$AGENTS_DIR/index-analyzer.md" "$GLOBAL_AGENTS_DIR/index-analyzer.md"
    print_status success "Installed index-analyzer subagent to $GLOBAL_AGENTS_DIR"
else
    print_status warning "index-analyzer.md not found in $AGENTS_DIR/"
    echo "   The -i flag may not work properly without this subagent"
fi

# Test installation
echo
echo "Testing installation..."
if uv run "$INDEXER_SCRIPT" --version 2>/dev/null | grep -q "3.0.0"; then
    print_status success "Installation test passed"
else
    print_status warning "Version check failed, but installation completed"
    echo "   You can still use the hooks normally"
fi

# Interactive additional hooks installation
echo
echo -e "${BLUE}=== Additional Hooks Installation ===${NC}"
echo
echo "Would you like to install additional hooks for enhanced functionality?"
echo "(These are optional and can be customized later)"
echo

# Helper Hooks Installation
echo -e "${YELLOW}📦 Helper Hooks${NC}"
echo "   Provides:"
echo "   • Git status display on session start"
echo "   • Safety protection (rm -rf blocking)"
echo "   • Session notifications and TTS support"
echo "   • Automatic context loading"
echo
read -p "Install Helper Hooks? (y/n): " install_helper

if [[ "$install_helper" == "y" || "$install_helper" == "Y" ]]; then
    if validate_hook_script "$HELPER_SCRIPT" "Helper hooks"; then
        add_hooks_to_settings "$HELPER_SCRIPT" "Helper" "${HELPER_HOOKS[@]}"
    fi
else
    echo "Skipping Helper Hooks installation"
fi

echo

# Rules Hook Installation
echo -e "${YELLOW}📋 Rules Hook${NC}"
echo "   Provides:"
echo "   • Auto-loads project rules from .claude/rules/"
echo "   • File pattern matching for automatic rule loading"
echo "   • Enforces planning before code changes"
echo "   • Commit reminders for modified files"
echo "   • Context-aware development workflow"
echo
read -p "Install Rules Hook? (y/n): " install_rules

if [[ "$install_rules" == "y" || "$install_rules" == "Y" ]]; then
    if validate_hook_script "$RULES_SCRIPT" "Rules hook"; then
        add_hooks_to_settings "$RULES_SCRIPT" "Rules" "${RULES_HOOKS[@]}"
    fi
else
    echo "Skipping Rules Hook installation"
fi

# Show installed hooks summary
echo
echo -e "${BLUE}=== Installed Hooks Summary ===${NC}"
echo
echo -e "${GREEN}✓${NC} Indexer Hooks (Always installed):"
echo "   • UserPromptSubmit: Detects -i flag for index-aware mode"
echo "   • SessionStart: Auto-indexes on session start"
echo "   • PreCompact: Updates index before compacting"
echo "   • Stop: Updates index on session end"

if [[ "$install_helper" == "y" || "$install_helper" == "Y" ]]; then
    echo
    echo -e "${GREEN}✓${NC} Helper Hooks:"
    echo "   • SessionStart: Shows git status and loads context"
    echo "   • PreToolUse: Blocks dangerous commands"
    echo "   • Stop: Session notifications"
    echo "   • Notification: Custom notifications"
    echo "   • SubagentStop: Subagent completion notifications"
fi

if [[ "$install_rules" == "y" || "$install_rules" == "Y" ]]; then
    echo
    echo -e "${GREEN}✓${NC} Rules Hook:"
    echo "   • UserPromptSubmit: Validates prompts against project rules"
    echo "   • PreToolUse: Enforces planning and loads rules by file patterns"
    echo "   • Stop: Reminds to commit changes"
    echo "   • SessionStart: Loads project context"
fi

# Final instructions
echo
echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo
echo "📁 Installation location: $PROJECT_ROOT/.claude"
echo
echo "🚀 Usage:"
echo "   • Type /index in any project to create/update the index"
echo "   • Add -i flag to any prompt for index-aware mode (e.g., 'fix auth bug -i')"
echo "     This triggers the index-analyzer subagent for deep code analysis"
echo "   • Use -ic flag to export to clipboard for large context AI models"
echo "   • Reference with @PROJECT_INDEX.json when you need architectural awareness"
echo "   • The index is created automatically when you use -i flag"
echo
echo "📝 Manual usage:"
echo "   • Command: /index (in Claude Code)"
echo "   • Direct: uv run $INDEXER_SCRIPT --project-index"
echo "   Both create PROJECT_INDEX.json in the current directory"
echo
echo "📍 Global hooks installed with absolute paths:"
echo "   • All hooks point to: $PROJECT_ROOT/.claude/hooks/"
echo "   • Works from any project directory"
echo
echo -e "${BLUE}Happy coding with the Indexer Hook!${NC}"