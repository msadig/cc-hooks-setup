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
jq --arg indexer_script "$INDEXER_SCRIPT" '
  # Initialize hooks if not present
  if .hooks == null then .hooks = {} else . end |
  
  # Add UserPromptSubmit hook for -i flag detection (append to existing)
  if .hooks.UserPromptSubmit == null then .hooks.UserPromptSubmit = [] else . end |
  .hooks.UserPromptSubmit += [{
    "hooks": [{
      "type": "command",
      "command": ("uv run " + $indexer_script + " --i-flag-hook"),
      "timeout": 20
    }]
  }] |
  
  # Add SessionStart hook for automatic indexing (append to existing) 
  if .hooks.SessionStart == null then .hooks.SessionStart = [] else . end |
  .hooks.SessionStart += [{
    "hooks": [{
      "type": "command", 
      "command": ("uv run " + $indexer_script + " --session-start"),
      "timeout": 5
    }]
  }] |
  
  # Add PreCompact hook (append to existing)
  if .hooks.PreCompact == null then .hooks.PreCompact = [] else . end |
  .hooks.PreCompact += [{
    "hooks": [{
      "type": "command",
      "command": ("uv run " + $indexer_script + " --precompact"), 
      "timeout": 15
    }]
  }] |
  
  # Add Stop hook (append to existing)
  if .hooks.Stop == null then .hooks.Stop = [] else . end |
  .hooks.Stop += [{
    "hooks": [{
      "type": "command",
      "command": ("uv run " + $indexer_script + " --stop"),
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
\`uv run $INDEXER_SCRIPT --project-index\`

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
    HELPER_SCRIPT="$HOOKS_DIR/helper_hooks.py"
    
    if [ ! -f "$HELPER_SCRIPT" ]; then
        echo -e "${RED}❌ Helper hooks script not found at: $HELPER_SCRIPT${NC}"
    else
        # Test if helper_hooks.py is executable
        if uv run "$HELPER_SCRIPT" --help &> /dev/null; then
            echo "Installing Helper Hooks..."
            
            # Update settings.json with helper hooks
            jq --arg helper_script "$HELPER_SCRIPT" '
              # Add SessionStart hook for git status and context
              if .hooks.SessionStart == null then .hooks.SessionStart = [] else . end |
              .hooks.SessionStart += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $helper_script + " session_start --load-context"),
                  "timeout": 10
                }]
              }] |
              
              # Add PreToolUse hook for safety checks
              if .hooks.PreToolUse == null then .hooks.PreToolUse = [] else . end |
              .hooks.PreToolUse += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $helper_script + " pre_tool_use"),
                  "timeout": 5
                }]
              }] |
              
              # Add Stop hook for notifications
              if .hooks.Stop == null then .hooks.Stop = [] else . end |
              .hooks.Stop += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $helper_script + " stop --announce"),
                  "timeout": 10
                }]
              }] |
              
              # Add Notification hook
              if .hooks.Notification == null then .hooks.Notification = [] else . end |
              .hooks.Notification += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $helper_script + " notification"),
                  "timeout": 5
                }]
              }] |
              
              # Add SubagentStop hook
              if .hooks.SubagentStop == null then .hooks.SubagentStop = [] else . end |
              .hooks.SubagentStop += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $helper_script + " subagent_stop"),
                  "timeout": 5
                }]
              }]
            ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
            
            echo -e "${GREEN}✓${NC} Helper Hooks installed successfully"
        else
            echo -e "${YELLOW}⚠${NC} Could not verify helper_hooks.py, skipping installation"
        fi
    fi
else
    echo "Skipping Helper Hooks installation"
fi

echo

# Rules Hook Installation
echo -e "${YELLOW}📋 Rules Hook${NC}"
echo "   Provides:"
echo "   • Auto-loads project rules from .claude/rules/"
echo "   • Enforces planning before code changes"
echo "   • Commit reminders for modified files"
echo "   • Context-aware development workflow"
echo
read -p "Install Rules Hook? (y/n): " install_rules

if [[ "$install_rules" == "y" || "$install_rules" == "Y" ]]; then
    RULES_SCRIPT="$HOOKS_DIR/rules_hook.py"
    
    if [ ! -f "$RULES_SCRIPT" ]; then
        echo -e "${RED}❌ Rules hook script not found at: $RULES_SCRIPT${NC}"
    else
        # Test if rules_hook.py is executable
        if uv run "$RULES_SCRIPT" --help &> /dev/null; then
            echo "Installing Rules Hook..."
            
            # Update settings.json with rules hooks
            jq --arg rules_script "$RULES_SCRIPT" '
              # Add UserPromptSubmit hook for prompt validation
              if .hooks.UserPromptSubmit == null then .hooks.UserPromptSubmit = [] else . end |
              .hooks.UserPromptSubmit += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $rules_script + " --prompt-validator"),
                  "timeout": 10
                }]
              }] |
              
              # Add PreToolUse hook for plan enforcement
              if .hooks.PreToolUse == null then .hooks.PreToolUse = [] else . end |
              .hooks.PreToolUse += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $rules_script + " --plan-enforcer"),
                  "timeout": 5
                }]
              }] |
              
              # Add Stop hook for commit helper
              if .hooks.Stop == null then .hooks.Stop = [] else . end |
              .hooks.Stop += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $rules_script + " --commit-helper"),
                  "timeout": 10
                }]
              }] |
              
              # Add SessionStart hook for context loading
              if .hooks.SessionStart == null then .hooks.SessionStart = [] else . end |
              .hooks.SessionStart += [{
                "hooks": [{
                  "type": "command",
                  "command": ("uv run " + $rules_script + " --session-start"),
                  "timeout": 10
                }]
              }]
            ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
            
            echo -e "${GREEN}✓${NC} Rules Hook installed successfully"
        else
            echo -e "${YELLOW}⚠${NC} Could not verify rules_hook.py, skipping installation"
        fi
    fi
else
    echo "Skipping Rules Hook installation"
fi

echo

# Show installed hooks summary
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
    echo "   • PreToolUse: Enforces planning before file changes"
    echo "   • Stop: Reminds to commit changes"
    echo "   • SessionStart: Loads project context"
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
echo "   • Direct: uv run $INDEXER_SCRIPT --project-index"
echo "   Both create PROJECT_INDEX.json in the current directory"
echo
echo "📍 Global hooks installed with absolute paths:"
echo "   • All hooks point to: $INDEXER_SCRIPT"
echo "   • Works from any project directory"
echo
echo -e "${BLUE}Happy coding with the Indexer Hook!${NC}"