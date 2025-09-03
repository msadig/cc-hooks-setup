# Claude Code Hook Ecosystem

A comprehensive hook system for Claude Code featuring rule enforcement, agent suggestions, and intelligent project indexing.

## Systems

### 🔧 Rule Enforcement System
- **Priority-Based Rule Loading**: Rules sorted by priority (critical > high > medium > low)
- **Smart Context Management**: Shows summaries or full content based on priority and triggers
- **Always Load Summary**: Critical rules can be configured to always show summaries
- **Intelligent Agent Suggestions**: Automatically recommends specialized agents based on triggered rules
- **Plan Enforcement**: Requires approved plans before code modifications
- **File Tracking**: Tracks all modified files for testing and commit
- **Generic Testing**: Works with any project type (JavaScript, Python, Go, etc.)
- **Auto-Commit Support**: Prompts for testing and committing at session end
- **Unified Hook Handler**: Single script (`rules_hook.py`) with flag-based routing

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

### 1. Priority-Based Rule Loading with Agent Suggestions (UserPromptSubmit)
When you submit a prompt, `rules_hook.py --prompt-validator`:
- Checks for keywords in your prompt
- Sorts rules by priority (critical > high > medium > low)
- Loads rules based on the loading matrix:
  - **Critical**: Always shows summary, full content if triggered or `always_load_summary=true`
  - **High**: Shows summary if triggered, full content based on configuration
  - **Medium**: Shows summary only when triggered
  - **Low**: Shows reference only when triggered
- Displays a priority summary table
- **Suggests specialized agents** (see [How Agent Recommendations Work](#how-agent-recommendations-work) below)
- Injects appropriate content as context for Claude

### 2. Plan Enforcement (PreToolUse)
Before any file modification, `rules_hook.py --plan-enforcer`:
- Checks if a plan exists in `.claude/sessions/[session-id]/current_plan.md`
- Verifies the plan is approved (`.claude/sessions/[session-id]/plan_approved` exists)
- Tracks modified files to `.claude/sessions/[session-id]/changed_files.txt`

### 3. Testing & Commit (Stop)
At session end, `rules_hook.py --commit-helper`:
- Reads the list of changed files
- Prompts Claude to run appropriate tests
- Requests commit with descriptive message

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

The hooks are configured in `.claude/settings.json`. The rule enforcement system uses `$CLAUDE_PROJECT_DIR` environment variable, while the indexer system uses absolute paths to ensure global availability.

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