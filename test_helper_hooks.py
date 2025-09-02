#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Test suite for unified helper_hooks.py script
"""

import json
import subprocess
import os
import tempfile
from pathlib import Path

def run_hook(hook_type, args="", input_data=None):
    """Helper function to run hook with input data."""
    cmd = f"uv run ./helper_hooks.py {hook_type} {args}"
    
    if input_data:
        process = subprocess.run(
            cmd,
            shell=True,
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )
    else:
        process = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
    
    return process.returncode, process.stdout, process.stderr

def test_user_prompt_submit():
    """Test user_prompt_submit hook."""
    print("Testing user_prompt_submit hook...")
    
    # Test basic logging
    input_data = {"session_id": "test-session", "prompt": "test prompt"}
    returncode, stdout, stderr = run_hook("user_prompt_submit", "--log-only", input_data)
    
    if returncode == 0:
        print("  ✅ Basic logging works")
    else:
        print(f"  ❌ Basic logging failed: {stderr}")
    
    # Test validation (should pass with empty blocked patterns)
    returncode, stdout, stderr = run_hook("user_prompt_submit", "--validate", input_data)
    
    if returncode == 0:
        print("  ✅ Validation passes for safe prompt")
    else:
        print(f"  ❌ Validation failed unexpectedly: {stderr}")

def test_session_start():
    """Test session_start hook."""
    print("\nTesting session_start hook...")
    
    # Test basic functionality
    input_data = {"source": "startup"}
    returncode, stdout, stderr = run_hook("session_start", "", input_data)
    
    if returncode == 0:
        print("  ✅ Basic session start works")
    else:
        print(f"  ❌ Session start failed: {stderr}")
    
    # Test with context loading
    returncode, stdout, stderr = run_hook("session_start", "--load-context", input_data)
    
    if returncode == 0 and stdout:
        try:
            output = json.loads(stdout)
            if "hookSpecificOutput" in output:
                print("  ✅ Context loading works")
            else:
                print("  ❌ Context loading returned unexpected format")
        except json.JSONDecodeError:
            print(f"  ❌ Context loading returned invalid JSON: {stdout}")
    else:
        print(f"  ❌ Context loading failed: {stderr}")

def test_pre_tool_use():
    """Test pre_tool_use hook."""
    print("\nTesting pre_tool_use hook...")
    
    # Test safe command
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"}
    }
    returncode, stdout, stderr = run_hook("pre_tool_use", "", input_data)
    
    if returncode == 0:
        print("  ✅ Safe command allowed")
    else:
        print(f"  ❌ Safe command blocked unexpectedly: {stderr}")
    
    # Test dangerous rm command
    input_data = {
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /"}
    }
    returncode, stdout, stderr = run_hook("pre_tool_use", "", input_data)
    
    if returncode == 2 and "BLOCKED" in stderr:
        print("  ✅ Dangerous rm command blocked")
    else:
        print(f"  ❌ Dangerous rm command not blocked properly")
    
    # Test .env file access
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/path/to/.env"}
    }
    returncode, stdout, stderr = run_hook("pre_tool_use", "", input_data)
    
    if returncode == 2 and "BLOCKED" in stderr:
        print("  ✅ .env file access blocked")
    else:
        print(f"  ❌ .env file access not blocked properly")
    
    # Test .env.sample is allowed
    input_data = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/path/to/.env.sample"}
    }
    returncode, stdout, stderr = run_hook("pre_tool_use", "", input_data)
    
    if returncode == 0:
        print("  ✅ .env.sample file access allowed")
    else:
        print(f"  ❌ .env.sample file access blocked unexpectedly: {stderr}")

def test_post_tool_use():
    """Test post_tool_use hook."""
    print("\nTesting post_tool_use hook...")
    
    input_data = {
        "tool_name": "Bash",
        "tool_output": "command output",
        "exit_code": 0
    }
    returncode, stdout, stderr = run_hook("post_tool_use", "", input_data)
    
    if returncode == 0:
        print("  ✅ Post tool use logging works")
    else:
        print(f"  ❌ Post tool use failed: {stderr}")

def test_pre_compact():
    """Test pre_compact hook."""
    print("\nTesting pre_compact hook...")
    
    input_data = {
        "trigger": "limit",
        "transcript_path": "/tmp/test_transcript.json"
    }
    returncode, stdout, stderr = run_hook("pre_compact", "", input_data)
    
    if returncode == 0:
        print("  ✅ Pre-compact logging works")
    else:
        print(f"  ❌ Pre-compact failed: {stderr}")

def test_stop():
    """Test stop hook."""
    print("\nTesting stop hook...")
    
    input_data = {
        "session_id": "test-session",
        "exit_code": 0
    }
    returncode, stdout, stderr = run_hook("stop", "", input_data)
    
    if returncode == 0:
        print("  ✅ Stop hook works")
    else:
        print(f"  ❌ Stop hook failed: {stderr}")

def test_notification():
    """Test notification hook."""
    print("\nTesting notification hook...")
    
    input_data = {
        "text": "Test notification"
    }
    returncode, stdout, stderr = run_hook("notification", "", input_data)
    
    if returncode == 0:
        print("  ✅ Notification hook works")
    else:
        print(f"  ❌ Notification hook failed: {stderr}")

def test_subagent_stop():
    """Test subagent_stop hook."""
    print("\nTesting subagent_stop hook...")
    
    input_data = {
        "subagent_id": "test-subagent",
        "exit_code": 0
    }
    returncode, stdout, stderr = run_hook("subagent_stop", "", input_data)
    
    if returncode == 0:
        print("  ✅ Subagent stop hook works")
    else:
        print(f"  ❌ Subagent stop hook failed: {stderr}")

def test_invalid_hook_type():
    """Test invalid hook type handling."""
    print("\nTesting invalid hook type...")
    
    # This should fail with exit code 2 due to argparse error
    process = subprocess.run(
        "uv run ./helper_hooks.py invalid_hook",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if process.returncode != 0:
        print("  ✅ Invalid hook type rejected")
    else:
        print("  ❌ Invalid hook type not rejected properly")

def main():
    print("=" * 50)
    print("Testing Unified helper_hooks.py")
    print("=" * 50)
    
    # Run all tests
    test_user_prompt_submit()
    test_session_start()
    test_pre_tool_use()
    test_post_tool_use()
    test_pre_compact()
    test_stop()
    test_notification()
    test_subagent_stop()
    test_invalid_hook_type()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()