# File Matcher with Reference Links - Example Usage

## How It Works

When Claude works with a file, it sees:

```
## Rules for: test.tsx

### CRITICAL
• Security - Follow security best practices, no secrets in code [@.claude/rules/security.md]

### MEDIUM
• Code Quality - Follow clean code principles and linting rules [@.claude/rules/code-quality.md]

💡 Reference [@filename] to see full rule details when needed
```

## Claude Can Now:

1. **See the summary** - Quick guidance on what to follow
2. **Know the priority** - CRITICAL rules are most important
3. **Access full details** - Use the `@.claude/rules/security.md` reference to read the complete rule file

## Example Interaction:

**User**: "I'm working on a login feature"

**Claude sees** (via file matcher when editing auth.tsx):
```
### CRITICAL
• Security - Follow security best practices, no secrets in code [@.claude/rules/security.md]
```

**Claude can then**:
```
I see this involves security. Let me check the full security rules...
@.claude/rules/security.md

[Reads the full security guidelines about authentication, password hashing, etc.]

Based on the security rules, I'll ensure we:
- Use bcrypt for password hashing
- Implement rate limiting
- Use secure session management
- Never log passwords
```

## Benefits:

1. **Efficient by default** - Only summaries shown initially (~30 tokens)
2. **Deep dive on demand** - Claude can read full rules when needed
3. **Context-aware** - Claude knows which files have detailed docs
4. **Self-service** - Claude can get more info without asking user

## Token Usage:

- **Initial load**: ~30-40 tokens (just summaries)
- **Full rule access**: Only when Claude needs it (optional)
- **Total savings**: 40-50% compared to always loading full rules