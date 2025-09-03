#!/bin/bash
set -eo pipefail

# Indexer Hook Uninstaller
# Removes Indexer Hook from Claude Code settings

echo "Indexer Hook Uninstaller"
echo "======================="
echo ""

# Get the directory where this script is located
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOKS_DIR="$PROJECT_ROOT/.claude/hooks"

echo "This will remove:"
echo "  • Indexer hooks from ~/.claude/settings.json"
echo "  • /index command from ~/.claude/commands/"
echo "  • index-analyzer subagent from ~/.claude/agents/"
echo ""
echo "⚠️  Note: This will NOT remove:"
echo "  • The Indexer Hook installation at $PROJECT_ROOT/.claude"
echo "  • Any PROJECT_INDEX.json files in your projects"
echo "  • Other existing hooks (rules_hook.py, helper_hooks.py, etc.)"
echo ""

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

echo ""
echo "Uninstalling Indexer Hook..."

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "❌ jq is not installed but is required for uninstall"
    echo "Please install jq first:"
    echo "  brew install jq  # on macOS"
    echo "  apt-get install jq  # on Ubuntu/Debian"
    exit 1
fi

# Remove hooks from settings.json
SETTINGS_FILE="$HOME/.claude/settings.json"
if [[ -f "$SETTINGS_FILE" ]]; then
    echo "Removing hooks from settings.json..."
    
    # Backup settings
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.uninstall-backup"
    
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
    
    echo "✓ Hooks removed from settings.json"
    echo "  Backup saved as: ${SETTINGS_FILE}.uninstall-backup"
else
    echo "• No settings.json found, skipping hook removal"
fi

# Remove /index command
INDEX_COMMAND="$HOME/.claude/commands/index.md"
if [[ -f "$INDEX_COMMAND" ]]; then
    rm "$INDEX_COMMAND"
    echo "✓ Removed /index command"
else
    echo "• No /index command found, skipping removal"
fi

# Remove index-analyzer subagent
INDEX_ANALYZER="$HOME/.claude/agents/index-analyzer.md"
if [[ -f "$INDEX_ANALYZER" ]]; then
    rm "$INDEX_ANALYZER"
    echo "✓ Removed index-analyzer subagent"
else
    echo "• No index-analyzer subagent found, skipping removal"
fi

echo ""
echo "=========================================="
echo "✅ Indexer Hook uninstalled!"
echo "=========================================="
echo ""
echo "📝 The Indexer Hook scripts remain at:"
echo "   $PROJECT_ROOT/.claude"
echo ""
echo "   You can still use them manually:"
echo "   • uv run $PROJECT_ROOT/.claude/hooks/indexer_hook.py --project-index"
echo ""
echo "📝 Manual cleanup (if desired):"
echo "   • Remove this installation: rm -rf $PROJECT_ROOT/.claude"
echo "   • Remove PROJECT_INDEX.json files from your projects:"
echo "     find ~ -name 'PROJECT_INDEX.json' -type f 2>/dev/null"
echo ""
echo "To reinstall the hooks, run:"
echo "   $PROJECT_ROOT/install.sh"