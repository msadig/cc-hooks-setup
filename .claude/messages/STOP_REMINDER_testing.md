# 🧪 Testing Reminder

Session ${session_id} ending - Remember to run tests!

## Test Commands
```bash
# Run unit tests
uv run pytest tests/

# Run the test for rules hook
uv run .claude/hooks/test_rules_hook.py
```

## Files to Test
${changed_files}

---
*This reminder brought to you by: ${template_file}*