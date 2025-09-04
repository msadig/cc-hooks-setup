#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Test script for file pattern matching functionality
"""
import json
import subprocess
import sys

def test_file_matcher(file_path, tool_name="Read"):
    """Test the file matcher hook with a given file path"""
    
    # Prepare the hook input
    hook_input = {
        "session_id": "test-session",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {
            "file_path": file_path
        }
    }
    
    # Run the hook
    cmd = ["uv", "run", ".claude/hooks/rules_hook.py", "--file-matcher"]
    
    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            cwd="/Users/sadigmuradov/Sadig/Development/playground/cc-hook-rules"
        )
        
        print(f"\n{'='*60}")
        print(f"Testing file: {file_path}")
        print(f"Tool: {tool_name}")
        print(f"{'='*60}")
        
        if result.stdout:
            try:
                output = json.loads(result.stdout)
                if "hookSpecificOutput" in output:
                    context = output["hookSpecificOutput"].get("additionalContext", "")
                    print(context)
                    # Count lines and approximate tokens for efficiency metrics
                    line_count = len(context.split('\n'))
                    approx_tokens = len(context.split())
                    print(f"\n📊 Output: {line_count} lines, ~{approx_tokens} tokens")
                else:
                    print("No additional context provided")
            except json.JSONDecodeError:
                print(f"Raw output: {result.stdout}")
        else:
            print("No rules matched for this file")
            
        if result.stderr:
            print(f"Errors: {result.stderr}")
            
        print(f"Exit code: {result.returncode}")
        
    except Exception as e:
        print(f"Error running hook: {e}")

# Test various file patterns
test_cases = [
    ("test_example.py", "Read"),  # Should match testing-standards
    ("src/components/Button.tsx", "Edit"),  # Should match code-quality
    ("README.md", "Write"),  # Should match documentation
    (".env.local", "Read"),  # Should match security
    ("settings.py", "Edit"),  # Should match security
    ("tests/unit/user.test.js", "Read"),  # Should match testing-standards
    ("random_file.txt", "Read"),  # Should not match any specific rule (only security if always_load)
]

print("File Pattern Matcher Test Suite")
print("================================\n")

for file_path, tool in test_cases:
    test_file_matcher(file_path, tool)
    
print("\n" + "="*60)
print("Test suite completed!")