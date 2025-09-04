#!/bin/bash

# Indexer Hook Uninstallation Script
# Removes Claude Code hooks and cleans up configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Claude Code configuration
CLAUDE_CONFIG_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_CONFIG_DIR/settings.json"

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

# Create timestamped backup
create_timestamped_backup() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="${SETTINGS_FILE}.backup.uninstall.${timestamp}"
    
    cp "$SETTINGS_FILE" "$backup_file"
    print_status success "Backup created: $backup_file"
}

# Function to remove specific hooks while preserving others in the same group
remove_hooks_from_group() {
    local hook_type=$1
    local hook_pattern=$2
    local temp_file="${SETTINGS_FILE}.tmp"
    
    # Use jq to filter out specific hooks within groups while preserving the group structure
    jq --arg type "$hook_type" --arg pattern "$hook_pattern" '
      if .hooks[$type] then
        .hooks[$type] = [
          .hooks[$type][] | 
          if .hooks then
            # Filter individual hooks within the group
            .hooks = [.hooks[] | select(.command | contains($pattern) | not)]
          else
            .
          end
        ] |
        # Remove empty groups
        .hooks[$type] = [.hooks[$type][] | select((.hooks | length) > 0)] |
        # Remove the entire hook type if no groups remain
        if (.hooks[$type] | length) == 0 then
          del(.hooks[$type])
        else
          .
        end
      else
        .
      end
    ' "$SETTINGS_FILE" > "$temp_file" && mv "$temp_file" "$SETTINGS_FILE"
}

# ==================== Main Uninstallation ====================

echo -e "${BLUE}=== Indexer Hook Uninstallation ===${NC}"
echo

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    print_status error "jq is not installed. Please install it first."
    exit 1
fi

# Check if settings.json exists
if [[ ! -f "$SETTINGS_FILE" ]]; then
    print_status warning "No Claude Code settings found at $SETTINGS_FILE"
    echo "Nothing to uninstall."
    exit 0
fi

# Create a backup
echo "Creating backup of current settings..."
create_timestamped_backup

echo
echo "Which hooks would you like to uninstall?"
echo "(You can choose to remove some or all)"
echo

# Track what was removed
removed_indexer=false
removed_helper=false
removed_rules=false

# Indexer Hooks
echo -e "${YELLOW}📁 Indexer Hooks${NC}"
echo "   Remove indexing functionality and -i flag support?"
read -p "Uninstall Indexer Hooks? (y/n): " uninstall_indexer

if [[ "$uninstall_indexer" == "y" || "$uninstall_indexer" == "Y" ]]; then
    echo "Removing Indexer hooks..."
    
    # Remove indexer hooks from each hook type
    remove_hooks_from_group "UserPromptSubmit" "indexer_hook.py --i-flag-hook"
    remove_hooks_from_group "SessionStart" "indexer_hook.py --session-start"
    remove_hooks_from_group "PreCompact" "indexer_hook.py --precompact"
    remove_hooks_from_group "Stop" "indexer_hook.py --stop"
    
    # Remove /index command
    INDEX_COMMAND="$HOME/.claude/commands/index.md"
    if [[ -f "$INDEX_COMMAND" ]]; then
        rm "$INDEX_COMMAND"
        echo -e "${GREEN}✓${NC} Removed /index command"
    fi
    
    # Remove index-analyzer subagent
    INDEX_ANALYZER="$HOME/.claude/agents/index-analyzer.md"
    if [[ -f "$INDEX_ANALYZER" ]]; then
        rm "$INDEX_ANALYZER"
        echo -e "${GREEN}✓${NC} Removed index-analyzer subagent"
    fi
    
    echo -e "${GREEN}✓${NC} Indexer Hooks removed"
    removed_indexer=true
else
    echo "Keeping Indexer Hooks"
fi

echo

# Helper Hooks
echo -e "${YELLOW}📦 Helper Hooks${NC}"
echo "   Remove git status, safety checks, and notifications?"
read -p "Uninstall Helper Hooks? (y/n): " uninstall_helper

if [[ "$uninstall_helper" == "y" || "$uninstall_helper" == "Y" ]]; then
    echo "Removing Helper hooks..."
    
    # Remove helper hooks from each hook type
    remove_hooks_from_group "SessionStart" "helper_hooks.py session_start"
    remove_hooks_from_group "PreToolUse" "helper_hooks.py pre_tool_use"
    remove_hooks_from_group "Stop" "helper_hooks.py stop"
    remove_hooks_from_group "Notification" "helper_hooks.py notification"
    remove_hooks_from_group "SubagentStop" "helper_hooks.py subagent_stop"
    
    echo -e "${GREEN}✓${NC} Helper Hooks removed"
    removed_helper=true
else
    echo "Keeping Helper Hooks"
fi

echo

# Rules Hook
echo -e "${YELLOW}📋 Rules Hook${NC}"
echo "   Remove project rules, file pattern matching, plan enforcement, and commit helpers?"
read -p "Uninstall Rules Hook? (y/n): " uninstall_rules

if [[ "$uninstall_rules" == "y" || "$uninstall_rules" == "Y" ]]; then
    echo "Removing Rules hook..."
    
    # Remove rules hooks from each hook type
    remove_hooks_from_group "UserPromptSubmit" "rules_hook.py --prompt-validator"
    remove_hooks_from_group "PreToolUse" "rules_hook.py --immutable-check"
    remove_hooks_from_group "PreToolUse" "rules_hook.py --plan-enforcer"
    remove_hooks_from_group "PreToolUse" "rules_hook.py --file-matcher"
    remove_hooks_from_group "Stop" "rules_hook.py --commit-helper"
    remove_hooks_from_group "SessionStart" "rules_hook.py --session-start"
    
    echo -e "${GREEN}✓${NC} Rules Hook removed"
    removed_rules=true
else
    echo "Keeping Rules Hook"
fi

# Clean up empty hooks object if everything was removed
jq 'if .hooks == {} then del(.hooks) else . end' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

# Summary
echo
echo -e "${BLUE}=== Uninstallation Summary ===${NC}"
echo

if $removed_indexer || $removed_helper || $removed_rules; then
    echo "Removed hooks:"
    [[ "$removed_indexer" == true ]] && echo -e "  ${GREEN}✓${NC} Indexer Hooks"
    [[ "$removed_helper" == true ]] && echo -e "  ${GREEN}✓${NC} Helper Hooks"
    [[ "$removed_rules" == true ]] && echo -e "  ${GREEN}✓${NC} Rules Hook"
    echo
    echo -e "${GREEN}Uninstallation complete!${NC}"
    echo "Your settings have been backed up to: ${SETTINGS_FILE}.backup.uninstall.*"
    echo
    echo "To reinstall, run: ./install.sh"
else
    echo "No hooks were removed."
fi

echo
echo -e "${BLUE}Thank you for using the Indexer Hook!${NC}"