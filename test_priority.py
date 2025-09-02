#!/usr/bin/env python3
"""
Test priority-based rule loading
"""
import json
import subprocess
import os

# Set the project directory
os.environ['CLAUDE_PROJECT_DIR'] = os.getcwd()

def test_case(description, prompt):
    """Run a test case and display output"""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Prompt: '{prompt}'")
    print("="*60)
    
    test_input = {"prompt": prompt}
    
    result = subprocess.run(
        ['python3', '.claude/hooks/prompt_validator.py'],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )
    
    print("Output:")
    print(result.stdout)
    
    if result.stderr:
        print("Errors:", result.stderr)
    
    return result.returncode == 0

# Run test cases
print("Testing Priority-Based Rule Loading System")
print("="*60)

# Test 1: No triggers (should show critical rule summary due to always_load_summary)
test_case(
    "No triggers - should show security summary (always_load_summary=true)",
    "I want to build a simple calculator app"
)

# Test 2: Security trigger (critical priority)
test_case(
    "Security trigger - should load full security content",
    "I need to implement authentication for the app"
)

# Test 3: Testing trigger (high priority)
test_case(
    "Testing trigger - should show testing content",
    "How do I write tests for this function?"
)

# Test 4: Multiple triggers with different priorities
test_case(
    "Multiple triggers - should sort by priority",
    "I need to test the security authentication module and document it"
)

# Test 5: Medium priority trigger
test_case(
    "Documentation trigger - medium priority, summary only",
    "I need to update the API documentation"
)

print("\n" + "="*60)
print("All tests completed!")
print("="*60)