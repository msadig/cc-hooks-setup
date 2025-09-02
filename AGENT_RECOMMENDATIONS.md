# How Agent Recommendations Work

## Simple Explanation

When you type a prompt, the system:
1. **Looks for keywords** in your prompt (like "test", "security", "documentation")
2. **Matches these to rules** defined in `.claude/rules/manifest.json`
3. **Suggests agents** that are experts in those areas

Think of it like autocomplete for expertise - if you mention testing, it suggests a testing expert.

## The Process (Step by Step)

### 1. You Type a Prompt
```
"I need to write tests for the API endpoints"
```

### 2. System Finds Keywords
The system looks for trigger words defined in `manifest.json`:
- Found: "test" → triggers `testing-standards` rule
- Found: "API" → triggers `documentation` rule

### 3. System Checks Agent Mappings
In `manifest.json`, under `metadata.agent_integrations`, each agent lists which rules it handles:
```json
"testing-specialist": {
  "related_rules": ["testing-standards"]
}
```

### 4. System Suggests Relevant Agents
If a triggered rule matches an agent's `related_rules`, that agent is suggested:
```
🤖 Recommended Agents:
- testing-specialist (because you triggered testing-standards)
```

## Example Configuration

Here's a minimal example showing how it works:

```json
{
  "rules": {
    "security": {
      "summary": "Security best practices",
      "triggers": ["auth", "password", "security"],  // Keywords to watch for
      "priority": "critical"
    }
  },
  "metadata": {
    "agent_integrations": {
      "security-auditor": {
        "related_rules": ["security"]  // This agent handles security rule - that's ALL you need!
      }
    }
  }
}
```

**What happens:**
- You type: "implement authentication"
- System finds: "auth" keyword
- Triggers: `security` rule
- Suggests: `security-auditor` agent (because it has "security" in related_rules)

## How to Add Your Own Agent Suggestions

### Step 1: Add a Rule
Add a new rule with trigger keywords:
```json
"rules": {
  "your-rule": {
    "summary": "What this rule does",
    "triggers": ["keyword1", "keyword2"],
    "priority": "medium"
  }
}
```

### Step 2: Map an Agent to the Rule
Add an agent that handles this rule:
```json
"agent_integrations": {
  "your-specialist": {
    "related_rules": ["your-rule"]  // That's it! Nothing else needed.
  }
}
```

### Step 3: Test It
Type a prompt with your keyword and see the agent suggestion appear!

## Current Agent Mappings

| Agent | Handles Rules | Triggered By Keywords |
|-------|--------------|----------------------|
| testing-specialist | testing-standards | test, testing, coverage, spec |
| security-auditor | security | security, auth, password, secret, token |
| code-quality-expert | code-quality, documentation | code, quality, lint, clean, docs, document, readme, api |

## Why This is Useful

1. **Reminds you** to use specialized agents for specific tasks
2. **Saves time** by suggesting the right tool for the job
3. **Improves quality** by matching expertise to needs

## What DOESN'T Matter (Removed Unnecessary Complexity)

These configurations do **nothing** in Claude Code and have been removed:
- **`enhanced`**: Was just decorative text
- **`automation_level`**: Didn't affect anything
- **`coverage_enforcement`**: Didn't actually enforce anything
- **`coverage_requirements`**: Didn't make anything mandatory
- **`consolidates`**: Redundant with `related_rules`

**The ONLY thing that matters** is the `related_rules` array that maps agents to rules.

## Simplification Ideas

If you find this too complex, you could:
1. **Remove agent suggestions** - Just delete the `agent_integrations` section
2. **Hardcode suggestions** - Always suggest the same agents regardless of context
3. **Use simpler matching** - Just check if certain words appear, without the rule system

The current system is now as simple as possible while still being useful!