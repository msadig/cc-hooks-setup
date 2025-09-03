# Claude Code Hook Ecosystem

A comprehensive hook system for Claude Code featuring rule enforcement, agent suggestions, and intelligent project indexing.

## Systems

### 🔧 Rule Enforcement System
- **Priority-Based Rule Loading**: Rules sorted by priority (critical > high > medium > low)
- **Smart Context Management**: Shows summaries or full content based on priority and triggers
- **Intelligent Agent Suggestions**: Automatically recommends specialized agents based on triggered rules
- **Glob Pattern Context Loading**: Flexible file discovery using .gitignore-like patterns (`.claude/**/WORKFLOW.md`, `.claude/**/*-CONTEXT.md`)
- **Consolidated Context Loading**: Unified approach for both UserPromptSubmit and SessionStart hooks
- **Plan Enforcement**: Requires approved plans before code modifications
- **File Tracking**: Tracks all modified files for testing and commit
- **Generic Testing**: Works with any project type (JavaScript, Python, Go, etc.)
- **Auto-Commit Support**: Prompts for testing and committing at session end
- **Unified Hook Handler**: Single script (`rules_hook.py`) with flag-based routing (`--prompt-validator`, `--session-start`, `--plan-enforcer`, `--commit-helper`)

### 📊 Indexer Hook System
- **Automatic Indexing**: Generates comprehensive project maps including directory structure, function signatures, call graphs, and dependencies
- **Index-Aware Mode**: Use `-i` flag to trigger intelligent code analysis via the index-analyzer subagent  
- **Clipboard Export**: Use `-ic` flag to export analysis prompts to external AI systems
- **Multiple Language Support**: Python, JavaScript, TypeScript, Swift, Shell, and Markdown parsing
- **Smart Caching**: Regenerates indices only when files change or size requirements differ
- **Hook Integration**: Seamlessly integrates with Claude Code's hook system

## Installation

### Rule Enforcement System (Already Active)
1. The hooks are already set up in `.claude/hooks/`
2. Settings are configured in `.claude/settings.json`
3. Rules are defined in `.claude/rules/manifest.json`

### Indexer Hook System
```bash
# Install the indexer hooks
./install.sh
```

The installer will:
- Verify dependencies (UV and jq)
- Add indexer hooks to your global Claude Code settings (~/.claude/settings.json)
- Use absolute paths to this project's indexer script
- Install the `/index` command globally
- Install the `index-analyzer` subagent globally

### Uninstalling Indexer Hooks
```bash
# Remove indexer hooks (keeps rule enforcement system)
./uninstall.sh
```

## Directory Structure

```
.claude/
├── hooks/
│   ├── rules_hook.py             # Rule enforcement and agent suggestions
│   ├── helper_hooks.py           # Session and utility hooks
│   ├── indexer_hook.py           # Main indexer with flag routing  
│   ├── test_indexer_hook.py      # Indexer test suite
│   └── utils/indexer/
│       ├── project_utils.py      # Project discovery and Git ops
│       ├── code_parsing.py       # Multi-language code analysis
│       ├── flag_hook.py          # Flag detection and processing
│       ├── project_indexer.py    # Core indexing and compression
│       └── test_*.py            # Test suites for all modules
├── agents/
│   └── index-analyzer.md         # Subagent for codebase analysis
├── rules/
│   ├── manifest.json             # Rule definitions and triggers
│   ├── testing-standards.md      # Testing requirements
│   ├── code-quality.md           # Code quality standards
│   ├── documentation.md          # Documentation requirements
│   └── security.md               # Security best practices
├── sessions/                     # Session-specific runtime state
│   └── [session-id]/
│       ├── current_plan.md       # Current implementation plan
│       ├── plan_approved         # Approval flag (empty file)
│       ├── loaded_rules.txt      # Which rules were loaded
│       └── changed_files.txt     # Files modified in session
└── settings.json                 # Hook configuration
```

## How It Works

### 1. Consolidated Context Loading & Rule System

**UserPromptSubmit** (`rules_hook.py --prompt-validator`):
- **Primary Context Files**: Uses glob patterns to find context files:
  - `docs/**/RULES.md`, `docs/**/MEMORY.md`, `docs/**/REQUIREMENTS.md`
  - `.claude/**/RULES.md`, `.claude/**/MEMORY.md`, `.claude/**/REQUIREMENTS.md`
- **Rule Processing**: Checks keywords, sorts by priority, applies loading matrix
- **Agent Suggestions**: Automatically recommends specialized agents based on triggered rules
- **Context Injection**: Provides unified context to Claude

**SessionStart** (`rules_hook.py --session-start`):
- **Project Context Files**: Uses glob patterns to discover:
  - `.claude/**/CONTEXT.md`, `.claude/**/WORKFLOW.md`, `.claude/**/SESSION.md`
  - `.claude/**/*-WORKFLOW.md`, `.claude/**/*-CONTEXT.md`
  - `TODO.md`, `.github/ISSUE_TEMPLATE.md`
- **Session Information**: Provides session details and project context
- **TTS Announcements**: Works with `helper_hooks.py` for audio notifications

### 2. Plan Enforcement (PreToolUse)
Before file modifications, `rules_hook.py --plan-enforcer`:
- Checks for approved plans in session directories
- Tracks all modified files for later processing
- Prevents modifications without proper planning

### 3. Commit Assistance (Stop)
At session end, `rules_hook.py --commit-helper`:
- Reviews all changed files tracked during the session
- Prompts for appropriate testing and validation
- Assists with descriptive commit messages

### 4. Indexer System Usage
The indexer hooks provide intelligent code analysis:

**Basic Usage:**
```bash
# Create/update project index
/index

# Use index-aware mode for any request
fix the authentication bug -i

# Export to clipboard for external AI
analyze the performance bottlenecks -ic50
```

**How it works:**
- **UserPromptSubmit**: Detects `-i` and `-ic` flags, generates/loads project index, triggers `index-analyzer` subagent
- **SessionStart**: Suggests index creation for new projects
- **PreCompact**: Backs up context state before compaction  
- **Stop**: Analyzes session and provides insights

## Glob Pattern Context Loading

The system uses .gitignore-like glob patterns for flexible context file discovery:

### Primary Context Files (UserPromptSubmit)
```yaml
Primary patterns (always loaded):
- "docs/**/RULES.md"           # Find RULES.md anywhere under docs/
- "docs/**/MEMORY.md"          # Find MEMORY.md anywhere under docs/
- "docs/**/REQUIREMENTS.md"    # Find REQUIREMENTS.md anywhere under docs/
- ".claude/**/RULES.md"        # Find RULES.md anywhere under .claude/
- ".claude/**/MEMORY.md"       # Find MEMORY.md anywhere under .claude/
- ".claude/**/REQUIREMENTS.md" # Find REQUIREMENTS.md anywhere under .claude/
```

### Project Context Files (SessionStart)
```yaml
Project patterns (session context):
- ".claude/**/CONTEXT.md"      # Find CONTEXT.md anywhere under .claude/
- ".claude/**/WORKFLOW.md"     # Find WORKFLOW.md anywhere under .claude/
- ".claude/**/SESSION.md"      # Find SESSION.md anywhere under .claude/
- ".claude/**/*-WORKFLOW.md"   # Find files ending with -WORKFLOW.md
- ".claude/**/*-CONTEXT.md"    # Find files ending with -CONTEXT.md
- "TODO.md"                    # Exact match for root TODO.md
- ".github/ISSUE_TEMPLATE.md"  # Exact match for issue template
```

### Benefits of Glob Patterns
- **Flexible Organization**: Context files can be organized in subdirectories
- **Naming Conventions**: Support for prefixes/suffixes (e.g., `team-WORKFLOW.md`)
- **Recursive Discovery**: `**` wildcard searches all subdirectory levels
- **Deduplication**: Automatic handling of files matched by multiple patterns
- **Consistent Ordering**: Files are sorted alphabetically for predictable output

### Example File Organization
```
.claude/
├── WORKFLOW.md              # Matches .claude/**/WORKFLOW.md
├── team/
│   ├── dev-WORKFLOW.md      # Matches .claude/**/*-WORKFLOW.md
│   └── CONTEXT.md           # Matches .claude/**/CONTEXT.md
└── projects/
    └── api/
        └── SESSION.md       # Matches .claude/**/SESSION.md
```

## Rule Loading Matrix

The system uses a priority-based loading matrix to manage context efficiently:

| Priority | always_load_summary | Keyword Match | Action |
|----------|-------------------|---------------|---------|
| critical | true | any | Load summary + full content |
| critical | false | yes | Load full content |
| high | true | any | Load summary |
| high | false | yes | Load summary + reference |
| medium | any | yes | Load summary only |
| low | any | yes | Load reference only |

## How Agent Recommendations Work

**Simple:** When you mention keywords like "test" or "security", the system suggests agents that specialize in those areas.

### Quick Example
```
You: "I need to write tests for the API"
     ↓
System: Finds keywords → "test" (triggers testing-standards rule)
                      → "API" (triggers documentation rule)
     ↓
System: Checks which agents handle these rules
     ↓
Output: 🤖 Recommended Agents:
        - testing-specialist (for testing-standards)
        - code-quality-expert (for documentation)
```

### Current Mappings
| Keywords You Type | Rule Triggered | Agent Suggested |
|------------------|----------------|-----------------|
| test, testing, coverage | testing-standards | testing-specialist |
| security, auth, password | security | security-auditor |
| docs, document, api | documentation | code-quality-expert |

### How to Use Suggested Agents
When you see an agent suggestion, you can use it by mentioning it in your next prompt:
```
"Use the testing-specialist agent to create comprehensive tests"
```

For more details, see [AGENT_RECOMMENDATIONS.md](./AGENT_RECOMMENDATIONS.md)

## Adding New Rules

1. Edit `.claude/rules/manifest.json` to add a new rule:
```json
{
  "rules": {
    "new-rule": {
      "summary": "Brief description",
      "file": "new-rule.md",
      "triggers": ["keyword1", "keyword2"],
      "priority": "high",
      "always_load_summary": false
    }
  },
  "metadata": {
    "agent_integrations": {
      "specialist-agent": {
        "related_rules": ["new-rule"]  // Simple: just map agent to rule
      }
    }
  }
}
```

2. Create the rule file `.claude/rules/new-rule.md` with your standards

## Testing

Run the test suite:
```bash
python3 .claude/hooks/test_rules_hook.py  # Complete test suite for all functionality
```

## Manual Workflow

1. **Create a plan**: Save it to `.claude/sessions/[session-id]/current_plan.md`
2. **Approve the plan**: Create empty file `.claude/sessions/[session-id]/plan_approved`
3. **Make changes**: The hooks will track all file modifications
4. **End session**: Claude will be prompted to test and commit

## Configuration

The hooks are configured in `.claude/settings.json` with a unified approach:

### Current Hook Configuration
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --prompt-validator"
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --session-start"
      }, {
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/helper_hooks.py session_start --announce"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --plan-enforcer"
      }]
    }, {
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/helper_hooks.py pre_tool_use --log"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --commit-helper"
      }, {
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/helper_hooks.py stop --announce"
      }]
    }]
  }
}
```

### Hook Architecture
- **Unified Handler**: `rules_hook.py` handles all rule enforcement, context loading, plan enforcement, and commit assistance
- **Helper Functions**: `helper_hooks.py` provides logging, notifications, and TTS announcements
- **Flag-Based Routing**: Single script with specific flags for different hook events
- **Environment Variables**: Uses `$CLAUDE_PROJECT_DIR` for project-relative paths

## Principles

- **K.I.S.S.**: Simple file-based state management
- **No OOP**: All scripts use simple functions
- **Generic**: Works with any project type
- **Unified**: Single hook script with flag-based routing
- **Intelligent**: Suggests specialized agents based on context

## Credits & Inspirations

This project combines and extends ideas from several excellent Claude Code hook implementations:

### 📊 **Project Indexing System**
- **Inspiration**: [claude-code-project-index](https://github.com/ericbuess/claude-code-project-index/) by Eric Buess
- **What we adapted**: Comprehensive project mapping, function signatures, call graphs, and dependency analysis
- **Our enhancements**: Multi-language support, smart caching, flag-based routing, clipboard export

### 🔧 **Dynamic Rule Loading**
- **Inspiration**: [ai-rules](https://github.com/sahin/ai-rules/) by Sahin
- **What we adapted**: Keyword-triggered rule loading and context injection
- **Our enhancements**: Priority-based loading matrix, agent suggestions, plan enforcement, glob pattern matching

### 🛠️ **Helper Hooks Foundation**
- **Inspiration**: [claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) by Disler
- **What we adapted**: Session logging, notifications, and utility hook patterns
- **Our enhancements**: Unified hook handler, file tracking, safety validations, TTS announcements

### 🙏 **Special Thanks**

A huge thanks to these developers for sharing their innovative approaches to Claude Code hook systems. Their work provided the foundation and inspiration for building this comprehensive hook ecosystem.

I've combined these approaches into a unified, extensible system that maintains the best aspects of each while adding new capabilities like agent suggestions, glob pattern matching, and priority-based rule loading.