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
AGENTS_DIR="$PROJECT_ROOT/.claude/agents"

echo -e "${BLUE}=== Indexer Hook Installation ===${NC}"
echo

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ UV is not installed${NC}"
    echo "Please install UV first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  or"
    echo "  brew install uv"
    exit 1
fi

echo -e "${GREEN}✓${NC} UV is installed"

# Check for jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is not installed${NC}"
    echo "Please install jq first:"
    echo "  brew install jq  # on macOS"
    echo "  apt-get install jq  # on Ubuntu/Debian"
    exit 1
fi

echo -e "${GREEN}✓${NC} jq is installed"

# Check for Claude Code configuration directory
CLAUDE_CONFIG_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_CONFIG_DIR/settings.json"

if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating Claude Code config directory...${NC}"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

echo -e "${GREEN}✓${NC} Claude Code directory exists"

# Verify project structure
if [ ! -f "$INDEXER_SCRIPT" ]; then
    echo -e "${RED}❌ Indexer script not found at: $INDEXER_SCRIPT${NC}"
    echo "Make sure you're running this from the project root directory"
    exit 1
fi

echo -e "${GREEN}✓${NC} Project structure verified"

# Test UV can run the indexer script
echo
echo "Testing UV execution..."
if uv run "$INDEXER_SCRIPT" --help &> /dev/null; then
    echo -e "${GREEN}✓${NC} UV can execute indexer script"
else
    echo -e "${YELLOW}⚠${NC} UV test failed, but hooks may still work"
fi

# Update hooks in settings.json
echo
echo "Configuring hooks..."

# Ensure settings.json exists
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "{}" > "$SETTINGS_FILE"
fi

# Create a backup
cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup"

# Update hooks using jq - adds indexer hooks to existing structure
jq --arg project_root "$PROJECT_ROOT" '
  # Initialize hooks if not present
  if .hooks == null then .hooks = {} else . end |
  
  # Add UserPromptSubmit hook for -i flag detection (append to existing)
  if .hooks.UserPromptSubmit == null then .hooks.UserPromptSubmit = [] else . end |
  .hooks.UserPromptSubmit += [{
    "hooks": [{
      "type": "command",
      "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/indexer_hook.py --i-flag-hook",
      "timeout": 20
    }]
  }] |
  
  # Add SessionStart hook for automatic indexing (append to existing) 
  if .hooks.SessionStart == null then .hooks.SessionStart = [] else . end |
  .hooks.SessionStart += [{
    "hooks": [{
      "type": "command", 
      "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/indexer_hook.py --session-start",
      "timeout": 5
    }]
  }] |
  
  # Add PreCompact hook (append to existing)
  if .hooks.PreCompact == null then .hooks.PreCompact = [] else . end |
  .hooks.PreCompact += [{
    "hooks": [{
      "type": "command",
      "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/indexer_hook.py --precompact", 
      "timeout": 15
    }]
  }] |
  
  # Add Stop hook (append to existing)
  if .hooks.Stop == null then .hooks.Stop = [] else . end |
  .hooks.Stop += [{
    "hooks": [{
      "type": "command",
      "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/indexer_hook.py --stop",
      "timeout": 45
    }]
  }]
' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

echo -e "${GREEN}✓${NC} Hooks configured in settings.json"

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
\`uv run \$CLAUDE_PROJECT_DIR/.claude/hooks/indexer_hook.py --project-index\`

## Troubleshooting

If the index is too large for your project, ask Claude:
"The indexer creates too large an index. Please modify it to only index src/ and lib/ directories"

For other issues, the tool is designed to be customized - just describe your problem to Claude!
EOF

echo -e "${GREEN}✓${NC} Created /index command"

# Install index-analyzer subagent
echo
echo "Installing index-analyzer subagent..."
GLOBAL_AGENTS_DIR="$HOME/.claude/agents"
mkdir -p "$GLOBAL_AGENTS_DIR"

# Copy the index-analyzer agent if it exists
if [ -f "$AGENTS_DIR/index-analyzer.md" ]; then
    cp "$AGENTS_DIR/index-analyzer.md" "$GLOBAL_AGENTS_DIR/index-analyzer.md"
    echo -e "${GREEN}✓${NC} Installed index-analyzer subagent to $GLOBAL_AGENTS_DIR"
else
    echo -e "${YELLOW}⚠${NC} index-analyzer.md not found in $AGENTS_DIR/"
    echo "   The -i flag may not work properly without this subagent"
fi

# Test installation
echo
echo "Testing installation..."
if uv run "$INDEXER_SCRIPT" --version 2>/dev/null | grep -q "3.0.0"; then
    echo -e "${GREEN}✓${NC} Installation test passed"
else
    echo -e "${YELLOW}⚠${NC} Version check failed, but installation completed"
    echo "   You can still use the hooks normally"
fi

# Instructions for usage
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
echo "   • Direct: uv run $PROJECT_ROOT/.claude/hooks/indexer_hook.py --project-index"
echo "   Both create PROJECT_INDEX.json in the current directory"
echo
echo -e "${BLUE}Happy coding with the Indexer Hook!${NC}"