# Claude Code Hook Ecosystem

A comprehensive hook system for Claude Code featuring rule enforcement, agent suggestions, and intelligent project indexing.

## Systems

### 📊 Enhanced Status Line
- **Two-Line Display**: Project/directory info on line 1, metrics on line 2
- **Context Tracking**: Visual percentage with color coding (green/yellow/red)
- **Time Estimation**: Shows time until context reset and actual reset time
- **Cost Analysis**: Displays total cost and hourly rate
- **Token Metrics**: Shows total tokens used and tokens per minute
- **Subtle Color Scheme**: Cyan for time, yellow for cost, magenta for metrics
- **Visual Indicators**: 🧠 for context, ⏳ for time, 💰 for cost, 📊 for metrics

### 🔧 Rule Enforcement System
- **Priority-Based Rule Loading**: Rules sorted by priority (critical > high > medium > low)
- **Smart Context Management**: Shows summaries or full content based on priority and triggers
- **Intelligent Agent Suggestions**: Automatically recommends specialized agents based on triggered rules
- **File Pattern Matching**: Automatically loads relevant rules based on file types being edited (e.g., `*.test.js`, `settings.py`, `*.tsx`)
- **Glob Pattern Context Loading**: Flexible file discovery using .gitignore-like patterns (`.claude/**/WORKFLOW.md`, `.claude/**/*-CONTEXT.md`)
- **Consolidated Context Loading**: Unified approach for both UserPromptSubmit and SessionStart hooks
- **Plan Enforcement**: Requires approved plans before code modifications
- **File Tracking**: Tracks all modified files for testing and commit
- **Generic Testing**: Works with any project type (JavaScript, Python, Go, etc.)
- **Auto-Commit Support**: Prompts for testing and committing at session end
- **Immutable Files Protection**: Prevents editing of sensitive files based on configurable patterns
- **PreToolUse File Matcher**: Loads relevant rules when working with specific file patterns
- **Unified Hook Handler**: Single script (`rules_hook.py`) with flag-based routing (`--prompt-validator`, `--session-start`, `--plan-enforcer`, `--commit-helper`, `--file-matcher`, `--immutable-check`)

### 📊 Indexer Hook System
- **Automatic Indexing**: Generates comprehensive project maps including directory structure, function signatures, call graphs, and dependencies
- **Index-Aware Mode**: Use `-i` flag to trigger intelligent code analysis via the index-analyzer subagent  
- **Clipboard Export**: Use `-ic` flag to export analysis prompts to external AI systems
- **Multiple Language Support**: Python, JavaScript, TypeScript, Swift, Shell, and Markdown parsing
- **Smart Caching**: Regenerates indices only when files change or size requirements differ
- **Hook Integration**: Seamlessly integrates with Claude Code's hook system

## Enhanced Features

### 🎤 Text-to-Speech (TTS) System
- **Multiple Provider Support**: Automatically selects the best available TTS provider
- **Priority-based Selection**: 
  1. **ElevenLabs** (highest quality, requires API key)
  2. **OpenAI** (fast and reliable, requires API key)
  3. **pyttsx3** (offline fallback, no API needed)
- **Automatic Fallback**: Seamlessly switches to available providers
- **Session Announcements**: Optional voice notifications for session events

### 🤖 LLM Integration Utilities
- **OpenAI Integration** (`utils/llm/oai.py`):
  - Fast completions using gpt-4.1-nano
  - Session completion messages
  - Context-aware responses
- **Anthropic Integration** (`utils/llm/anth.py`):
  - Claude model support
  - Advanced reasoning capabilities
- **Flexible API Management**: Environment variable-based configuration

### 🧪 Comprehensive Testing Infrastructure
- **Full Test Coverage**: Test files for all major components
- **Module-specific Tests**:
  - `test_rules_hook.py`: Rule enforcement testing
  - `test_helper_hooks.py`: Helper function validation
  - `test_indexer_hook.py`: Indexer functionality tests
  - Individual tests for utils modules
- **Easy Test Execution**: All tests run via `uv run`

### ⚡ Performance & Reliability
- **Timeout Configuration**: Customizable timeouts for each hook type
- **Project-local Hook Support**: Enhanced `hook_exists` function for better discovery
- **Improved Command Checking**: More robust command availability detection
- **Modern Python Features**: Type hints, f-strings, match statements (Python 3.11+)

## Installation

### Prerequisites
- **Python 3.11+**: Required for modern syntax features and type hints
- **UV**: Python package and project manager ([installation guide](https://github.com/astral-sh/uv))
- **jq**: JSON processor (for indexer functionality)
- **Optional API Keys** (for enhanced features):
  - `ELEVENLABS_API_KEY`: For ElevenLabs TTS support
  - `OPENAI_API_KEY`: For OpenAI TTS and LLM features
  - `ANTHROPIC_API_KEY`: For Anthropic LLM features

### Rule Enforcement System (Already Active)
1. The hooks are already set up in `.claude/hooks/`
2. Settings are configured in `.claude/settings.json`
3. Rules are defined in `.claude/rules/manifest.json`
4. All Python hooks use `uv run` for execution

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
├── statusline.sh                 # Enhanced two-line status display
├── hooks/
│   ├── rules_hook.py             # Rule enforcement and agent suggestions
│   ├── helper_hooks.py           # Unified hook helper with all functionality
│   ├── indexer_hook.py           # Main indexer with flag routing  
│   ├── test_rules_hook.py        # Rule enforcement test suite
│   ├── test_helper_hooks.py      # Helper hooks test suite
│   ├── test_indexer_hook.py      # Indexer test suite
│   └── utils/
│       ├── llm/                  # LLM integration utilities
│       │   ├── oai.py            # OpenAI integration
│       │   └── anth.py           # Anthropic integration
│       ├── tts/                  # Text-to-Speech providers
│       │   ├── elevenlabs_tts.py # ElevenLabs TTS (priority 1)
│       │   ├── openai_tts.py     # OpenAI TTS (priority 2)
│       │   └── pyttsx3_tts.py    # Offline TTS (fallback)
│       └── indexer/
│           ├── project_utils.py   # Project discovery and Git ops
│           ├── code_parsing.py    # Multi-language code analysis
│           ├── flag_hook.py       # Flag detection and processing
│           ├── project_indexer.py # Core indexing and compression
│           └── test_*.py          # Test suites for all modules
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
- **Optional TTS Announcements**: Can be configured with `helper_hooks.py session_start --announce`

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

### 4. File Pattern Matching (PreToolUse)
When working with files, `rules_hook.py --file-matcher`:
- Detects file patterns during Read/Write/Edit operations
- Automatically loads rules matching the file type
- Provides context-aware guidance based on file patterns
- Groups rules by priority for clear presentation

### 5. Immutable Files Protection (PreToolUse)
Before file modifications, `rules_hook.py --immutable-check`:
- Checks if file matches immutable patterns defined in manifest.json
- Blocks editing of sensitive files (e.g., `.ssh/*`, `*.key`, `*.pem`)
- Supports glob patterns including recursive directory matching (`**/`)
- Provides clear error messages when blocking operations

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

## Immutable Files Protection

The system can protect sensitive files from being edited through configurable patterns in `manifest.json`:

### How It Works
1. Define patterns in `.claude/rules/manifest.json` under `metadata.immutable_files`
2. The hook checks every write/edit operation against these patterns
3. Operations are blocked with a clear error message if a match is found

### Pattern Examples
```json
"immutable_files": [
  "**/.ssh/*",        // Protect all SSH files in any .ssh directory
  "*.key",            // Protect all private key files
  "*.pem",            // Protect all PEM certificate files
  "**/secrets/*",     // Protect all files in any secrets directory
  "*.env.production", // Protect production environment files
  "**/.git/config",   // Protect git configuration
  "**/node_modules/*" // Prevent editing dependencies
]
```

### Supported Pattern Types
- **Exact match**: `config.json`
- **Wildcard**: `*.key`, `test_*.py`
- **Directory**: `secrets/*`
- **Recursive**: `**/.ssh/*`, `**/private/*`
- **Multiple levels**: `src/**/*.test.js`

This feature helps prevent accidental modification of critical system files, credentials, and sensitive configuration.

## File Pattern-Based Rule Loading

The system can automatically load rules when you're working with specific file types:

### How It Works
1. Define `file_matchers` in your rule definition in `manifest.json`
2. When you read/write/edit a file, matching rules are automatically loaded
3. Rules are presented grouped by priority with helpful context

### Configuration Example
```json
"testing-standards": {
  "summary": "Testing requirements and standards",
  "file": "testing-standards.md",
  "triggers": ["test", "testing", "coverage"],
  "file_matchers": ["*.test.js", "*.spec.ts", "test_*.py", "**/tests/*"],
  "priority": "high"
}
```

### Use Cases
- **Testing Files**: Load testing standards when editing test files
- **Configuration Files**: Load security rules when editing config files
- **API Files**: Load API documentation rules when editing endpoints
- **Component Files**: Load frontend standards when editing React/Vue components

This ensures developers see relevant rules exactly when they need them, improving compliance and code quality.

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
      "always_load_summary": false,
      "file_matchers": ["*.test.js", "*.spec.ts"]  // Optional: load rule for specific file patterns
    }
  },
  "metadata": {
    "agent_integrations": {
      "specialist-agent": {
        "related_rules": ["new-rule"]  // Simple: just map agent to rule
      }
    },
    "immutable_files": [  // Optional: patterns for files that cannot be edited
      "**/.ssh/*",
      "*.key",
      "*.pem",
      "**/secrets/*",
      "*.env.production"
    ]
  }
}
```

2. Create the rule file `.claude/rules/new-rule.md` with your standards

## Testing

Run the comprehensive test suite using UV (Python package manager):
```bash
# Test rule enforcement and hook system
uv run .claude/hooks/test_rules_hook.py

# Test helper hooks functionality
uv run .claude/hooks/test_helper_hooks.py

# Test indexer functionality
uv run .claude/hooks/test_indexer_hook.py

# Run specific test modules
uv run .claude/hooks/utils/indexer/test_project_utils.py
uv run .claude/hooks/utils/indexer/test_code_parsing.py
uv run .claude/hooks/utils/indexer/test_flag_hook.py
```

**Note**: All Python scripts in this project use `uv` for dependency management and execution. Tests cover all major components including TTS integration, LLM utilities, and hook routing.

## Manual Workflow

1. **Create a plan**: Save it to `.claude/sessions/[session-id]/current_plan.md`
2. **Approve the plan**: Create empty file `.claude/sessions/[session-id]/plan_approved`
3. **Make changes**: The hooks will track all file modifications
4. **End session**: Claude will be prompted to test and commit

## Configuration

The hooks and statusline are configured in `.claude/settings.json` with a unified approach:

### Status Line Configuration
```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

### Current Hook Configuration
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --prompt-validator",
        "timeout": 10
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --session-start",
        "timeout": 10
      }]
    }],
    "PreToolUse": [{
      "matcher": "Write|Edit|MultiEdit|NotebookEdit",
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --immutable-check",
        "timeout": 5
      }]
    }, {
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --plan-enforcer",
        "timeout": 5
      }]
    }, {
      "matcher": "Read|Write|Edit|MultiEdit|NotebookEdit",
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --file-matcher",
        "timeout": 5
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/rules_hook.py --commit-helper",
        "timeout": 10
      }]
    }]
  }
}
```

### Hook Architecture
- **Unified Handler**: `rules_hook.py` handles all rule enforcement, context loading, plan enforcement, commit assistance, file pattern matching, and immutable files protection
- **Helper Functions**: `helper_hooks.py` provides a unified interface for all utility hooks with modernized Python 3.11+ syntax
- **Flag-Based Routing**: Scripts use specific flags for different hook events:
  - `--prompt-validator`: Loads rules based on keywords in user prompts
  - `--session-start`: Provides project context at session start
  - `--plan-enforcer`: Enforces planning before file modifications
  - `--commit-helper`: Assists with testing and committing changes
  - `--file-matcher`: Loads rules based on file patterns being edited
  - `--immutable-check`: Prevents editing of sensitive files
- **Environment Variables**: Uses `$CLAUDE_PROJECT_DIR` for project-relative paths
- **Session Management**: Tracks state per session in `.claude/sessions/[session-id]/`
- **Timeout Configuration**: Each hook has configurable timeout settings for reliability
- **TTS Integration**: Automatic provider selection based on available API keys
- **LLM Support**: Optional AI-powered messages and completions

## Principles

- **K.I.S.S.**: Simple file-based state management
- **Modern Python**: Leverages Python 3.11+ features (type hints, f-strings, match statements)
- **No OOP**: All scripts use simple functions for maintainability
- **Generic**: Works with any project type (JavaScript, Python, Go, etc.)
- **Unified**: Single hook scripts with flag-based routing
- **Intelligent**: Suggests specialized agents based on context
- **Extensible**: Easy to add new TTS providers, LLM integrations, or hook types
- **Reliable**: Timeout configurations and fallback mechanisms

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