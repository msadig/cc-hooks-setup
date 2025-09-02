#!/usr/bin/env python3
"""
Test script to verify hook functionality
"""
import json
import subprocess
import os
import tempfile

# Set the project directory
os.environ['CLAUDE_PROJECT_DIR'] = os.getcwd()

def test_prompt_validator():
    """Test the prompt_validator.py hook"""
    print("Testing prompt_validator.py...")
    
    # Test input with security keyword
    test_input = {
        "prompt": "I need to implement authentication and security features"
    }
    
    result = subprocess.run(
        ['python3', '.claude/hooks/prompt_validator.py'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if "Security Standards" in result.stdout:
        print("✅ prompt_validator.py: Successfully loaded security rules")
    else:
        print("❌ prompt_validator.py: Failed to load security rules")
        print(f"Output: {result.stdout}")
    
    # Check if loaded_rules.txt was created
    if os.path.exists('.claude/session/loaded_rules.txt'):
        with open('.claude/session/loaded_rules.txt', 'r') as f:
            rules = f.read()
            print(f"   Loaded rules: {rules}")
    
    return result.returncode == 0

def test_plan_enforcer():
    """Test the plan_enforcer.py hook"""
    print("\nTesting plan_enforcer.py...")
    
    # Test without plan (should block)
    test_input = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/test/file.py"
        }
    }
    
    result = subprocess.run(
        ['python3', '.claude/hooks/plan_enforcer.py'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 2 and "No plan found" in result.stderr:
        print("✅ plan_enforcer.py: Correctly blocked operation without plan")
    else:
        print("❌ plan_enforcer.py: Should have blocked operation")
    
    # Create a plan and approval flag
    os.makedirs('.claude/session', exist_ok=True)
    with open('.claude/session/current_plan.md', 'w') as f:
        f.write("# Test Plan\n\nThis is a test plan.")
    
    # Test with plan but no approval (should block)
    result = subprocess.run(
        ['python3', '.claude/hooks/plan_enforcer.py'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 2 and "not approved" in result.stderr:
        print("✅ plan_enforcer.py: Correctly blocked unapproved plan")
    else:
        print("❌ plan_enforcer.py: Should have blocked unapproved plan")
    
    # Create approval flag
    open('.claude/session/plan_approved', 'w').close()
    
    # Test with approved plan (should pass)
    result = subprocess.run(
        ['python3', '.claude/hooks/plan_enforcer.py'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ plan_enforcer.py: Correctly allowed approved operation")
        
        # Check if file was tracked
        if os.path.exists('.claude/session/changed_files.txt'):
            with open('.claude/session/changed_files.txt', 'r') as f:
                files = f.read()
                print(f"   Tracked files: {files.strip()}")
    else:
        print("❌ plan_enforcer.py: Should have allowed approved operation")
    
    return True

def test_commit_helper():
    """Test the commit_helper.py hook"""
    print("\nTesting commit_helper.py...")
    
    # Clean up any previous test files
    import shutil
    if os.path.exists('.claude/session'):
        shutil.rmtree('.claude/session')
    
    # Test with no changed files
    result = subprocess.run(
        ['python3', '.claude/hooks/commit_helper.py'],
        input='{}',
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and not result.stdout.strip():
        print("✅ commit_helper.py: Correctly handled no changes")
    else:
        print("❌ commit_helper.py: Should exit silently with no changes")
        print(f"   Output: '{result.stdout}'")
    
    # Test with changed files
    os.makedirs('.claude/session', exist_ok=True)
    with open('.claude/session/changed_files.txt', 'w') as f:
        f.write("file1.py\nfile2.js\n")
    
    result = subprocess.run(
        ['python3', '.claude/hooks/commit_helper.py'],
        input='{}',
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0 and result.stdout:
        output = json.loads(result.stdout)
        if output.get('decision') == 'block' and 'file1.py' in output.get('reason', ''):
            print("✅ commit_helper.py: Correctly prompted for testing and commit")
            print(f"   Reason: {output.get('reason')}")
        else:
            print("❌ commit_helper.py: Output format incorrect")
    else:
        print("❌ commit_helper.py: Should have prompted for commit")
    
    return True

def cleanup():
    """Clean up test files"""
    import shutil
    if os.path.exists('.claude/session'):
        shutil.rmtree('.claude/session')
    print("\n✅ Cleaned up test files")

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Hook-Based Rule Enforcement System")
    print("=" * 50)
    
    try:
        # Run tests
        test_prompt_validator()
        test_plan_enforcer()
        test_commit_helper()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        print("=" * 50)
    finally:
        cleanup()