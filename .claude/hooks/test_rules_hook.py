#!/usr/bin/env python3
"""
Test script to verify rules_hook.py functionality
"""
import json
import subprocess
import sys
import os
import tempfile

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_prompt_validator():
    """Test prompt validator functionality"""
    print("Testing prompt validator...")
    
    # Create test input
    test_input = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "test security implementation",
        "session_id": "test-session"
    }
    
    # Run the rules hook with --prompt-validator flag
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py", "--prompt-validator"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    # Check if it ran successfully
    if result.returncode == 0:
        print("✅ Prompt validator test passed")
        if "Project Rules Loaded" in result.stdout:
            print("  - Rules loading confirmed")
        if "security" in result.stdout.lower():
            print("  - Security rule triggered as expected")
    else:
        print(f"❌ Prompt validator test failed: {result.stderr}")
    
    return result.returncode == 0

def test_plan_enforcer():
    """Test plan enforcer functionality"""
    print("\nTesting plan enforcer...")
    
    # Create test session directory with plan
    session_id = "test-session-plan"
    session_dir = f"{PROJECT_DIR}/.claude/sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    # Test without plan (should block)
    test_input = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.txt"},
        "session_id": session_id
    }
    
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py", "--plan-enforcer"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 2 and "No plan found" in result.stderr:
        print("✅ Plan enforcer correctly blocks without plan")
    else:
        print("❌ Plan enforcer should block without plan")
        return False
    
    # Create plan and approval
    with open(f"{session_dir}/current_plan.md", "w") as f:
        f.write("Test plan")
    open(f"{session_dir}/plan_approved", "w").close()
    
    # Test with plan (should pass)
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py", "--plan-enforcer"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Plan enforcer allows operation with approved plan")
        # Check if file was tracked
        if os.path.exists(f"{session_dir}/changed_files.txt"):
            with open(f"{session_dir}/changed_files.txt", "r") as f:
                if "/tmp/test.txt" in f.read():
                    print("  - File tracking confirmed")
    else:
        print(f"❌ Plan enforcer should allow with plan: {result.stderr}")
        return False
    
    # Cleanup
    os.system(f"rm -rf {session_dir}")
    
    return True

def test_commit_helper():
    """Test commit helper functionality"""
    print("\nTesting commit helper...")
    
    # Create test session with changed files
    session_id = "test-session-commit"
    session_dir = f"{PROJECT_DIR}/.claude/sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    # Test without changed files (should not block)
    test_input = {
        "hook_event_name": "Stop",
        "session_id": session_id
    }
    
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py", "--commit-helper"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and not result.stdout:
        print("✅ Commit helper doesn't block without changes")
    else:
        print("❌ Commit helper should not block without changes")
        return False
    
    # Add changed files
    with open(f"{session_dir}/changed_files.txt", "w") as f:
        f.write("/tmp/file1.txt\n/tmp/file2.txt\n")
    
    # Test with changed files (should block and request commit)
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py", "--commit-helper"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and result.stdout:
        output = json.loads(result.stdout)
        if output.get("decision") == "block" and "commit" in output.get("reason", "").lower():
            print("✅ Commit helper blocks and requests commit")
            print("  - Changed files detected and reported")
        else:
            print("❌ Commit helper should block with changes")
            return False
    else:
        print("❌ Commit helper failed with changes")
        return False
    
    # Cleanup
    os.system(f"rm -rf {session_dir}")
    
    return True

def test_flag_routing():
    """Test that flags properly route to handlers"""
    print("\nTesting flag-based routing...")
    
    # Test that events without correct flags don't trigger
    test_input = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "test",
        "session_id": "test"
    }
    
    # Run without any flags (should do nothing)
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and not result.stdout:
        print("✅ No handler triggered without flags")
    else:
        print("❌ Should not trigger without flags")
        return False
    
    # Run with wrong flag (should do nothing)
    result = subprocess.run(
        [sys.executable, f"{PROJECT_DIR}/.claude/hooks/rules_hook.py", "--commit-helper"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and not result.stdout:
        print("✅ Wrong flag doesn't trigger handler")
    else:
        print("❌ Wrong flag shouldn't trigger")
        return False
    
    return True

def main():
    print("=" * 50)
    print("Testing Rules Hook Functionality")
    print("=" * 50)
    
    all_passed = True
    
    # Run all tests
    all_passed &= test_prompt_validator()
    all_passed &= test_plan_enforcer()
    all_passed &= test_commit_helper()
    all_passed &= test_flag_routing()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All tests passed! Functionality preserved.")
    else:
        print("❌ Some tests failed. Please review.")
    print("=" * 50)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())