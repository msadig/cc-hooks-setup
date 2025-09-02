# Hook-Based Rule Enforcement System

A simple, K.I.S.S.-compliant hook system for Claude Code that automatically loads and enforces project-specific rules.

## Features

- **Priority-Based Rule Loading**: Rules sorted by priority (critical > high > medium > low)
- **Smart Context Management**: Shows summaries or full content based on priority and triggers
- **Always Load Summary**: Critical rules can be configured to always show summaries
- **Plan Enforcement**: Requires approved plans before code modifications
- **File Tracking**: Tracks all modified files for testing and commit
- **Generic Testing**: Works with any project type (JavaScript, Python, Go, etc.)
- **Auto-Commit Support**: Prompts for testing and committing at session end

## Installation

1. The hooks are already set up in `.claude/hooks/`
2. Settings are configured in `.claude/settings.json`
3. Rules are defined in `.claude/rules/manifest.json`

## Directory Structure

```
.claude/
├── hooks/
│   ├── prompt_validator.py    # Loads rules based on keywords
│   ├── plan_enforcer.py       # Enforces plan approval
│   └── commit_helper.py       # Handles testing and commits
├── rules/
│   ├── manifest.json          # Rule definitions and triggers
│   ├── testing-standards.md   # Testing requirements
│   ├── code-quality.md        # Code quality standards
│   ├── documentation.md       # Documentation requirements
│   └── security.md            # Security best practices
├── session/                   # Runtime state (auto-created)
│   ├── current_plan.md       # Current implementation plan
│   ├── plan_approved         # Approval flag (empty file)
│   ├── loaded_rules.txt      # Which rules were loaded
│   └── changed_files.txt     # Files modified in session
└── settings.json              # Hook configuration
```

## How It Works

### 1. Priority-Based Rule Loading (UserPromptSubmit)
When you submit a prompt, `prompt_validator.py`:
- Checks for keywords in your prompt
- Sorts rules by priority (critical > high > medium > low)
- Loads rules based on the loading matrix:
  - **Critical**: Always shows summary, full content if triggered or `always_load_summary=true`
  - **High**: Shows summary if triggered, full content based on configuration
  - **Medium**: Shows summary only when triggered
  - **Low**: Shows reference only when triggered
- Displays a priority summary table
- Injects appropriate content as context for Claude

### 2. Plan Enforcement (PreToolUse)
Before any file modification, `plan_enforcer.py`:
- Checks if a plan exists in `.claude/session/current_plan.md`
- Verifies the plan is approved (`.claude/session/plan_approved` exists)
- Tracks modified files to `.claude/session/changed_files.txt`

### 3. Testing & Commit (Stop)
At session end, `commit_helper.py`:
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
  }
}
```

2. Create the rule file `.claude/rules/new-rule.md` with your standards

## Testing

Run the test suites:
```bash
python3 test_hooks.py      # Basic functionality tests
python3 test_priority.py   # Priority-based loading tests
```

## Manual Workflow

1. **Create a plan**: Save it to `.claude/session/current_plan.md`
2. **Approve the plan**: Create empty file `.claude/session/plan_approved`
3. **Make changes**: The hooks will track all file modifications
4. **End session**: Claude will be prompted to test and commit

## Configuration

The hooks are configured in `.claude/settings.json`. The system uses `$CLAUDE_PROJECT_DIR` environment variable to ensure all paths work regardless of Claude's current directory.

## Principles

- **K.I.S.S.**: Simple file-based state management
- **No OOP**: All scripts use simple functions
- **Generic**: Works with any project type
- **Minimal**: Only 3 hook scripts, 1 tracking file