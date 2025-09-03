#!/bin/bash
set -eo pipefail

# Hook Uninstaller for Claude Code
# Interactively removes hooks from Claude Code settings

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Claude Code Hooks Uninstaller ===${NC}"
echo

# Get the directory where this script is located
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"

echo "This uninstaller can remove the following hooks from ~/.claude/settings.json:"
echo
echo -e "${YELLOW}📁 Indexer Hooks${NC}"
echo "   • UserPromptSubmit: -i flag detection"
echo "   • SessionStart: Auto-indexing"
echo "   • PreCompact: Index updates"
echo "   • Stop: Index on session end"
echo "   • /index command"
echo "   • index-analyzer subagent"
echo
echo -e "${YELLOW}📦 Helper Hooks${NC}"
echo "   • SessionStart: Git status display"
echo "   • PreToolUse: Safety checks"
echo "   • Stop: Session notifications"
echo "   • Notification: Custom notifications"
echo "   • SubagentStop: Subagent notifications"
echo
echo -e "${YELLOW}📋 Rules Hook${NC}"
echo "   • UserPromptSubmit: Prompt validation"
echo "   • PreToolUse: Plan enforcement"
echo "   • Stop: Commit helper"
echo "   • SessionStart: Context loading"
echo
echo -e "${YELLOW}⚠️  Note:${NC} This will NOT remove:"
echo "   • The hook scripts at $PROJECT_ROOT/.claude"
echo "   • Any PROJECT_INDEX.json files"
echo "   • Any custom hooks you've added"
echo

# Check if we're running interactively or via pipe
if [ -t 0 ]; then
    # Interactive mode - can use read
    read -p "Continue with uninstall? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstall cancelled"
        exit 0
    fi
else
    # Non-interactive mode - skip confirmation
    echo "Running in non-interactive mode, proceeding with uninstall..."
    echo ""
fi

echo

# Check for jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is not installed but is required for uninstall${NC}"
    echo "Please install jq first:"
    echo "  brew install jq  # on macOS"
    echo "  apt-get install jq  # on Ubuntu/Debian"
    exit 1
fi

SETTINGS_FILE="$HOME/.claude/settings.json"

# Check if settings.json exists
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo -e "${YELLOW}No settings.json found, nothing to uninstall${NC}"
    exit 0
fi

# Backup settings
echo "Creating backup..."
cp "$SETTINGS_FILE" "${SETTINGS_FILE}.uninstall-backup"
echo -e "${GREEN}✓${NC} Backup saved as: ${SETTINGS_FILE}.uninstall-backup"
echo

# Track what was removed
removed_indexer=false
removed_helper=false
removed_rules=false

# Interactive selection for each hook type
echo -e "${BLUE}=== Select Hooks to Uninstall ===${NC}"
echo

# Indexer Hooks
echo -e "${YELLOW}📁 Indexer Hooks${NC}"
echo "   Remove indexing functionality and -i flag support?"
read -p "Uninstall Indexer Hooks? (y/n): " uninstall_indexer

if [[ "$uninstall_indexer" == "y" || "$uninstall_indexer" == "Y" ]]; then
    echo "Removing Indexer hooks..."
    
    # Remove indexer hooks using jq - preserve other hooks
    jq '
      # Remove indexer UserPromptSubmit hooks
      if .hooks.UserPromptSubmit then
        .hooks.UserPromptSubmit = [.hooks.UserPromptSubmit[] | select(
          all(.hooks[]?.command // ""; 
            contains("indexer_hook.py --i-flag-hook") | not)
        )]
      else . end |
      
      # Remove indexer SessionStart hooks
      if .hooks.SessionStart then
        .hooks.SessionStart = [.hooks.SessionStart[] | select(
          all(.hooks[]?.command // ""; 
            contains("indexer_hook.py --session-start") | not)
        )]
      else . end |
      
      # Remove indexer PreCompact hooks
      if .hooks.PreCompact then
        .hooks.PreCompact = [.hooks.PreCompact[] | select(
          all(.hooks[]?.command // ""; 
            contains("indexer_hook.py --precompact") | not)
        )]
      else . end |
      
      # Remove indexer Stop hooks
      if .hooks.Stop then
        .hooks.Stop = [.hooks.Stop[] | select(
          all(.hooks[]?.command // ""; 
            contains("indexer_hook.py --stop") | not)
        )]
      else . end |
      
      # Clean up empty arrays (only if they are completely empty)
      if (.hooks.UserPromptSubmit // []) == [] then del(.hooks.UserPromptSubmit) else . end |
      if (.hooks.SessionStart // []) == [] then del(.hooks.SessionStart) else . end |
      if (.hooks.PreCompact // []) == [] then del(.hooks.PreCompact) else . end |
      if (.hooks.Stop // []) == [] then del(.hooks.Stop) else . end |
      
      # Clean up empty hooks object (only if completely empty)
      if .hooks == {} then del(.hooks) else . end
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    
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
    
    jq '
      # Remove helper SessionStart hooks
      if .hooks.SessionStart then
        .hooks.SessionStart = [.hooks.SessionStart[] | select(
          all(.hooks[]?.command // ""; 
            contains("helper_hooks.py session_start") | not)
        )]
      else . end |
      
      # Remove helper PreToolUse hooks
      if .hooks.PreToolUse then
        .hooks.PreToolUse = [.hooks.PreToolUse[] | select(
          all(.hooks[]?.command // ""; 
            contains("helper_hooks.py pre_tool_use") | not)
        )]
      else . end |
      
      # Remove helper Stop hooks
      if .hooks.Stop then
        .hooks.Stop = [.hooks.Stop[] | select(
          all(.hooks[]?.command // ""; 
            contains("helper_hooks.py stop") | not)
        )]
      else . end |
      
      # Remove helper Notification hooks
      if .hooks.Notification then
        .hooks.Notification = [.hooks.Notification[] | select(
          all(.hooks[]?.command // ""; 
            contains("helper_hooks.py notification") | not)
        )]
      else . end |
      
      # Remove helper SubagentStop hooks
      if .hooks.SubagentStop then
        .hooks.SubagentStop = [.hooks.SubagentStop[] | select(
          all(.hooks[]?.command // ""; 
            contains("helper_hooks.py subagent_stop") | not)
        )]
      else . end |
      
      # Clean up empty arrays
      if (.hooks.SessionStart // []) == [] then del(.hooks.SessionStart) else . end |
      if (.hooks.PreToolUse // []) == [] then del(.hooks.PreToolUse) else . end |
      if (.hooks.Stop // []) == [] then del(.hooks.Stop) else . end |
      if (.hooks.Notification // []) == [] then del(.hooks.Notification) else . end |
      if (.hooks.SubagentStop // []) == [] then del(.hooks.SubagentStop) else . end |
      
      # Clean up empty hooks object
      if .hooks == {} then del(.hooks) else . end
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    
    echo -e "${GREEN}✓${NC} Helper Hooks removed"
    removed_helper=true
else
    echo "Keeping Helper Hooks"
fi

echo

# Rules Hook
echo -e "${YELLOW}📋 Rules Hook${NC}"
echo "   Remove project rules, plan enforcement, and commit helpers?"
read -p "Uninstall Rules Hook? (y/n): " uninstall_rules

if [[ "$uninstall_rules" == "y" || "$uninstall_rules" == "Y" ]]; then
    echo "Removing Rules hook..."
    
    jq '
      # Remove rules UserPromptSubmit hooks
      if .hooks.UserPromptSubmit then
        .hooks.UserPromptSubmit = [.hooks.UserPromptSubmit[] | select(
          all(.hooks[]?.command // ""; 
            contains("rules_hook.py --prompt-validator") | not)
        )]
      else . end |
      
      # Remove rules PreToolUse hooks
      if .hooks.PreToolUse then
        .hooks.PreToolUse = [.hooks.PreToolUse[] | select(
          all(.hooks[]?.command // ""; 
            contains("rules_hook.py --plan-enforcer") | not)
        )]
      else . end |
      
      # Remove rules Stop hooks
      if .hooks.Stop then
        .hooks.Stop = [.hooks.Stop[] | select(
          all(.hooks[]?.command // ""; 
            contains("rules_hook.py --commit-helper") | not)
        )]
      else . end |
      
      # Remove rules SessionStart hooks
      if .hooks.SessionStart then
        .hooks.SessionStart = [.hooks.SessionStart[] | select(
          all(.hooks[]?.command // ""; 
            contains("rules_hook.py --session-start") | not)
        )]
      else . end |
      
      # Clean up empty arrays
      if (.hooks.UserPromptSubmit // []) == [] then del(.hooks.UserPromptSubmit) else . end |
      if (.hooks.PreToolUse // []) == [] then del(.hooks.PreToolUse) else . end |
      if (.hooks.Stop // []) == [] then del(.hooks.Stop) else . end |
      if (.hooks.SessionStart // []) == [] then del(.hooks.SessionStart) else . end |
      
      # Clean up empty hooks object
      if .hooks == {} then del(.hooks) else . end
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    
    echo -e "${GREEN}✓${NC} Rules Hook removed"
    removed_rules=true
else
    echo "Keeping Rules Hook"
fi

echo
echo -e "${BLUE}=== Uninstall Summary ===${NC}"
echo

# Show what was removed
if [[ "$removed_indexer" == true || "$removed_helper" == true || "$removed_rules" == true ]]; then
    echo -e "${GREEN}Removed hooks:${NC}"
    
    if [[ "$removed_indexer" == true ]]; then
        echo -e "  ${GREEN}✓${NC} Indexer Hooks"
        echo "      • Removed -i flag detection"
        echo "      • Removed auto-indexing"
        echo "      • Removed /index command"
        echo "      • Removed index-analyzer subagent"
    fi
    
    if [[ "$removed_helper" == true ]]; then
        echo -e "  ${GREEN}✓${NC} Helper Hooks"
        echo "      • Removed git status display"
        echo "      • Removed safety checks"
        echo "      • Removed session notifications"
    fi
    
    if [[ "$removed_rules" == true ]]; then
        echo -e "  ${GREEN}✓${NC} Rules Hook"
        echo "      • Removed prompt validation"
        echo "      • Removed plan enforcement"
        echo "      • Removed commit helpers"
    fi
    
    echo
else
    echo "No hooks were removed."
fi

# Show what remains
echo -e "${BLUE}Still installed:${NC}"

if [[ "$removed_indexer" == false ]]; then
    echo -e "  ${GREEN}•${NC} Indexer Hooks (active)"
fi

if [[ "$removed_helper" == false ]]; then
    echo -e "  ${GREEN}•${NC} Helper Hooks (active)"
fi

if [[ "$removed_rules" == false ]]; then
    echo -e "  ${GREEN}•${NC} Rules Hook (active)"
fi

if [[ "$removed_indexer" == true && "$removed_helper" == true && "$removed_rules" == true ]]; then
    echo "  None - all hooks have been removed"
fi

echo
echo -e "${YELLOW}📝 Note:${NC}"
echo "   • Hook scripts remain at: $PROJECT_ROOT/.claude"
echo "   • Backup saved as: ${SETTINGS_FILE}.uninstall-backup"
echo
echo "To reinstall hooks, run:"
echo "   $PROJECT_ROOT/install.sh"
echo
echo "To restore from backup:"
echo "   cp ${SETTINGS_FILE}.uninstall-backup $SETTINGS_FILE"