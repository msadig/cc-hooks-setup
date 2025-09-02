# Hook-Based Rule Enforcement System with Agent Suggestions

A simple, K.I.S.S.-compliant hook system for Claude Code that automatically loads and enforces project-specific rules and suggests specialized agents based on triggered rules.

## Features

- **Priority-Based Rule Loading**: Rules sorted by priority (critical > high > medium > low)
- **Smart Context Management**: Shows summaries or full content based on priority and triggers
- **Always Load Summary**: Critical rules can be configured to always show summaries
- **Intelligent Agent Suggestions**: Automatically recommends specialized agents based on triggered rules
- **Plan Enforcement**: Requires approved plans before code modifications
- **File Tracking**: Tracks all modified files for testing and commit
- **Generic Testing**: Works with any project type (JavaScript, Python, Go, etc.)
- **Auto-Commit Support**: Prompts for testing and committing at session end
- **Unified Hook Handler**: Single script (`rules_hook.py`) with flag-based routing

## Installation

1. The hooks are already set up in `.claude/hooks/`
2. Settings are configured in `.claude/settings.json`
3. Rules are defined in `.claude/rules/manifest.json`

## Directory Structure

```
.claude/
├── hooks/
│   ├── rules_hook.py          # Unified hook handler with all functionality
│   └── test_rules_hook.py     # Test suite for the hook
├── rules/
│   ├── manifest.json          # Rule definitions, triggers, and agent integrations
│   ├── testing-standards.md   # Testing requirements
│   ├── code-quality.md        # Code quality standards
│   ├── documentation.md       # Documentation requirements
│   └── security.md            # Security best practices
├── sessions/                  # Session-specific runtime state (auto-created)
│   └── [session-id]/
│       ├── current_plan.md    # Current implementation plan
│       ├── plan_approved      # Approval flag (empty file)
│       ├── loaded_rules.txt   # Which rules were loaded
│       └── changed_files.txt  # Files modified in session
└── settings.json              # Hook configuration
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
        "enhanced": true,
        "related_rules": ["new-rule"],
        "coverage_enforcement": "80%+",
        "automation_level": "high"
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

The hooks are configured in `.claude/settings.json`. The system uses `$CLAUDE_PROJECT_DIR` environment variable to ensure all paths work regardless of Claude's current directory.

## Principles

- **K.I.S.S.**: Simple file-based state management
- **No OOP**: All scripts use simple functions
- **Generic**: Works with any project type
- **Unified**: Single hook script with flag-based routing
- **Intelligent**: Suggests specialized agents based on context