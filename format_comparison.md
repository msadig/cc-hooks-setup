# File Matcher Output Format Comparison

## Old Format (Table-based)
```
## File-Based Rules Loaded for: test.tsx

### Applicable Rules
| Rule | Priority | Reason |
|------|----------|--------|
| Code-Quality | MEDIUM | 📁 File Pattern Match |
| Security | CRITICAL | 📋 Always Loaded |

---

### 📁 Code-Quality [PRIORITY: MEDIUM]
**Summary:** Follow clean code principles and linting rules
**Details:** See `.claude/rules/code-quality.md` if needed
```
**Metrics**: 13 lines, ~52 tokens

## New Format (Priority-grouped)
```
## Rules for: test.tsx

### CRITICAL
• Security - Follow security best practices, no secrets in code

### MEDIUM
• Code Quality - Follow clean code principles and linting rules
```
**Metrics**: 7 lines, ~30 tokens

## Improvements

| Metric | Old Format | New Format | Improvement |
|--------|------------|------------|-------------|
| Lines | 13 | 7 | **46% reduction** |
| Tokens | ~52 | ~30 | **42% reduction** |
| Structure | Table + Details | Priority Groups | Clearer hierarchy |
| Readability | Verbose | Concise | Better for AI |

## Benefits

1. **Token Efficiency**: ~40-50% reduction in token usage per file operation
2. **Clearer Priority**: Rules grouped by importance level
3. **Actionable Format**: Rule name + guidance in one line
4. **Simpler Parsing**: No table structure to parse
5. **Reduced Redundancy**: No duplicate information

Since PreToolUse runs on EVERY file Read/Write/Edit operation, this optimization saves significant tokens over a session.