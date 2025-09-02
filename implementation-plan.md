# Hook-Based Rule Enforcement System - Implementation Plan

## Overview
Build a Claude Code hooks system that automatically loads and enforces project-specific rules when a manifest file exists at `$CLAUDE_PROJECT_DIR/.claude/rules/manifest.json`.

## Architecture Components

### 1. Core Hook Scripts (Python, using `uv`)
- **prompt_validator.py** - UserPromptSubmit hook for rule injection
- **plan_enforcer.py** - PreToolUse hook for plan validation and file tracking
- **commit_helper.py** - Stop hook for auto-commit and test execution

### 2. State Management (Simple file-based)
- `.claude/session/current_plan.md` - The actual plan content (for QA review)
- `.claude/session/plan_approved` - Empty file acts as flag (exists = approved)
- `.claude/session/loaded_rules.txt` - List of loaded rule files (one per line)
- `.claude/session/changed_files.txt` - List of modified files (one per line, also used for testing)
- `.claude/session/test_results.txt` - Test output log (written by Claude)

### 3. Configuration Files
- `.claude/settings.json` - Hook configurations
- `.claude/rules/manifest.json` - Rule definitions
- `.claude/rules/*.md` - Rule markdown files

## Implementation Steps

### Phase 1: Foundation (Day 1)
1. **Build rule loader** - Simple keyword matching from manifest
2. **Setup state files** - Create session directory structure
3. **Configure UserPromptSubmit hook** - Load and inject rules

### Phase 2: Plan Enforcement (Day 2)
1. **Plan detection** - Check if response contains a plan
2. **Store plan** - Save to `current_plan.md`
3. **Approval gate** - Block execution until `plan_approved` file exists
4. **Simple validation** - Check plan exists before allowing edits

### Phase 3: Execution Tracking (Day 3)
1. **File tracking** - Append to `changed_files.txt` on each edit
2. **Smart test detection** - Use git diff to find what changed
3. **Test execution** - Run relevant tests, log to `test_results.txt`

### Phase 4: Session Completion (Day 4)
1. **Auto-commit** - Read `changed_files.txt`, commit those files
2. **Generate commit message** - Simple description based on plan
3. **Cleanup** - Archive session files

## Technical Implementation Details

### Path Management Using Environment Variable
**IMPORTANT**: Always use `$CLAUDE_PROJECT_DIR` environment variable for all file paths to avoid issues when Claude changes directories during work.

```python
import os

# Get project root from environment
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')

# Build paths relative to project root
SESSION_DIR = os.path.join(PROJECT_DIR, '.claude', 'session')
RULES_DIR = os.path.join(PROJECT_DIR, '.claude', 'rules')
MANIFEST_PATH = os.path.join(RULES_DIR, 'manifest.json')

# Use these paths consistently
PLAN_PATH = os.path.join(SESSION_DIR, 'current_plan.md')
APPROVED_FLAG = os.path.join(SESSION_DIR, 'plan_approved')
CHANGED_FILES = os.path.join(SESSION_DIR, 'changed_files.txt')
LOADED_RULES = os.path.join(SESSION_DIR, 'loaded_rules.txt')
TEST_RESULTS = os.path.join(SESSION_DIR, 'test_results.txt')
```

### Simplified State Management
```python
# No complex JSON parsing, just simple file operations

# Check if plan approved
def is_plan_approved():
    return os.path.exists(os.path.join(PROJECT_DIR, '.claude/session/plan_approved'))

# Track changed file
def track_file(filepath):
    session_dir = os.path.join(PROJECT_DIR, '.claude/session')
    with open(os.path.join(session_dir, 'changed_files.txt'), 'a') as f:
        f.write(f"{filepath}\n")

# Get changed files
def get_changed_files():
    changed_files_path = os.path.join(PROJECT_DIR, '.claude/session/changed_files.txt')
    if not os.path.exists(changed_files_path):
        return []
    with open(changed_files_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]
```

### Plan Storage Guidelines for AI
When Claude creates a plan, it should:
1. Save the plan to `.claude/session/current_plan.md`
2. Use this template format:
```markdown
# Implementation Plan

## Objective
[Brief description of what will be implemented]

## Tasks
- [ ] Task 1 description
- [ ] Task 2 description
- [ ] Task 3 description

## Files to Modify
- file1.ts
- file2.ts

## Testing Strategy
[How the implementation will be tested]

## Estimated Time
[Time estimate]
```

### Rule Loading (Simple)
```python
# prompt_validator.py
import json
import sys
import os

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')

# Read prompt from stdin
input_data = json.load(sys.stdin)
prompt = input_data.get('prompt', '').lower()

# Check if manifest exists
manifest_path = os.path.join(PROJECT_DIR, '.claude/rules/manifest.json')
if not os.path.exists(manifest_path):
    # No manifest, exit silently
    sys.exit(0)

# Load manifest
with open(manifest_path, 'r') as f:
    manifest = json.load(f)

# Simple keyword matching
rules_to_load = []
for rule_name, rule_data in manifest['rules'].items():
    # Check if any trigger keyword is in prompt
    for trigger in rule_data['triggers']:
        if trigger.lower() in prompt:
            rules_to_load.append(rule_data['file'])
            break

# Output rules as context
for rule_file in rules_to_load:
    rule_path = os.path.join(PROJECT_DIR, '.claude/rules', rule_file)
    if os.path.exists(rule_path):
        with open(rule_path, 'r') as f:
            print(f"### Rule: {rule_file}\n{f.read()}\n")

# Ensure session directory exists
session_dir = os.path.join(PROJECT_DIR, '.claude/session')
os.makedirs(session_dir, exist_ok=True)

# Save loaded rules list
loaded_rules_path = os.path.join(session_dir, 'loaded_rules.txt')
with open(loaded_rules_path, 'w') as f:
    f.write('\n'.join(rules_to_load))
```

### Plan Enforcement (Simple)
```python
# plan_enforcer.py
import json
import sys
import os

# Get project root
PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')
SESSION_DIR = os.path.join(PROJECT_DIR, '.claude/session')

input_data = json.load(sys.stdin)
tool_name = input_data.get('tool_name', '')

# Only check for Write/Edit operations
if tool_name in ['Write', 'Edit', 'MultiEdit']:
    # Ensure session directory exists
    os.makedirs(SESSION_DIR, exist_ok=True)
    
    # Check if plan exists and is approved
    plan_path = os.path.join(SESSION_DIR, 'current_plan.md')
    approved_flag = os.path.join(SESSION_DIR, 'plan_approved')
    
    if not os.path.exists(plan_path):
        print("No plan found. Please create a plan first.", file=sys.stderr)
        sys.exit(2)  # Block operation
    
    if not os.path.exists(approved_flag):
        print("Plan not approved. Please get approval first.", file=sys.stderr)
        sys.exit(2)  # Block operation
    
    # Track the file being modified
    tool_input = input_data.get('tool_input', {})
    filepath = tool_input.get('file_path', '')
    if filepath:
        changed_files_path = os.path.join(SESSION_DIR, 'changed_files.txt')
        with open(changed_files_path, 'a') as f:
            f.write(f"{filepath}\n")
```

### Commit Helper (Simple)
```python
# commit_helper.py
# At Stop hook, tells Claude to test and commit changes
import json
import sys
import os

PROJECT_DIR = os.environ.get('CLAUDE_PROJECT_DIR', '.')
SESSION_DIR = os.path.join(PROJECT_DIR, '.claude/session')

# Check if there are changed files
changed_files_path = os.path.join(SESSION_DIR, 'changed_files.txt')

changed_files = []
if os.path.exists(changed_files_path):
    with open(changed_files_path, 'r') as f:
        changed_files = [line.strip() for line in f if line.strip()]

if changed_files:
    # Tell Claude to run tests and commit
    output = {
        "decision": "block",
        "reason": f"Please run tests for these modified files and commit changes: {changed_files}"
    }
    print(json.dumps(output))
    sys.exit(0)
```

### Hook Configuration
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/prompt_validator.py"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/plan_enforcer.py"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/commit_helper.py"
      }]
    }]
  }
}
```

## Key Features (Simplified)
1. **Rule Loading** - Simple keyword matching, output as context
2. **Plan Storage** - Plain markdown file for QA review
3. **Approval Gate** - Simple file flag (exists = approved)
4. **File Tracking** - Single text file tracks all changed files
5. **Generic Testing** - Claude runs appropriate tests based on changed files
6. **Auto Commit** - Read file list, test, and commit with simple message

### Generic Testing Approach
Instead of hardcoding test runners for specific languages:
- PreToolUse hook tracks all modified files to `changed_files.txt`
- At Stop hook, commit_helper.py reads the list and tells Claude to test and commit
- Claude determines the appropriate test command based on:
  - Project type (package.json → npm/yarn, pyproject.toml → pytest, go.mod → go test, etc.)
  - File type and location
  - Existing test files and patterns
- This works for ANY project: Next.js, Python, Go, Flutter, monorepos, etc.

## Success Criteria
- ✅ Rules loaded based on keyword matching
- ✅ Plan stored as markdown for QA review
- ✅ Approval required before code changes
- ✅ Changed files tracked simply
- ✅ Related tests run automatically
- ✅ Changes auto-committed at session end

## What We're NOT Doing (K.I.S.S.)
- ❌ Complex JSON state management
- ❌ Parsing plan content for metadata
- ❌ Sophisticated scope extraction
- ❌ Complex dependency graphs
- ❌ Advanced metrics collection
- ❌ Multi-level validation

## Estimated Timeline
- **Day 1**: Basic rule loading and injection
- **Day 2**: Plan storage and approval gate
- **Day 3**: File tracking and smart testing
- **Day 4**: Auto-commit and cleanup
- **Total**: 4 days for full implementation

## Status
**APPROVED** - Ready for implementation