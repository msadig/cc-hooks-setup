#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyperclip",
# ]
# ///

"""
UserPromptSubmit hook for -i and -ic flag detection.
Generates project index at requested size and optionally copies to clipboard.
"""

import json
import sys
import os
import re
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
import pyperclip

from project_utils import find_project_root, should_index_file
from project_indexer import build_index, convert_to_enhanced_dense_format, compress_if_needed

def get_last_interactive_size():
    """Get the last remembered -i size from the index."""
    project_root = find_project_root()
    index_path = project_root / "PROJECT_INDEX.json"
    
    if not index_path.exists():
        return None
    
    try:
        with open(index_path, "r") as f:
            index = json.load(f)
            return index.get("last_interactive_size_k")
    except:
        return None

def parse_index_flag(prompt):
    """Parse -i or -ic flag with optional size."""
    # Pattern: -i or -ic with optional size, must be followed by space or end of string
    # This prevents matching words like "multi-index" or "-index"
    pattern = r'-i(c?)(\d+)?(?:\s|$)'
    match = re.search(pattern, prompt)
    
    if not match:
        return None, False
    
    is_clipboard = match.group(1) == 'c'
    size_str = match.group(2)
    
    if size_str:
        size_k = int(size_str)
    else:
        # Use last size or default
        size_k = get_last_interactive_size() or 50
    
    return size_k, is_clipboard

def calculate_files_hash(project_root):
    """Calculate hash of non-ignored files to detect changes."""
    try:
        # Use git ls-files if available
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            files = sorted(result.stdout.strip().split('\n'))
            # Create hash of file list and their modification times
            hash_content = []
            for file in files:
                file_path = project_root / file
                if file_path.exists():
                    stat = file_path.stat()
                    hash_content.append(f"{file}:{stat.st_mtime}:{stat.st_size}")
            
            combined = "\n".join(hash_content)
            return hashlib.md5(combined.encode()).hexdigest()
    except:
        pass
    
    # Fallback to simple directory listing
    all_files = []
    for path in project_root.rglob("*"):
        if path.is_file() and should_index_file(path, project_root):
            rel_path = path.relative_to(project_root)
            stat = path.stat()
            all_files.append(f"{rel_path}:{stat.st_mtime}:{stat.st_size}")
    
    combined = "\n".join(sorted(all_files))
    return hashlib.md5(combined.encode()).hexdigest()

def should_regenerate_index(project_root, index_path, requested_size_k):
    """Determine if index needs regeneration."""
    if not index_path.exists():
        return True, "No index exists"
    
    try:
        with open(index_path, "r") as f:
            index = json.load(f)
        
        # Check if size is different
        last_size = index.get("last_interactive_size_k", 0)
        if abs(last_size - requested_size_k) > 5:  # Allow 5k tolerance
            return True, f"Size changed: {last_size}k → {requested_size_k}k"
        
        # Check if files have changed
        current_hash = calculate_files_hash(project_root)
        stored_hash = index.get("files_hash", "")
        
        if current_hash != stored_hash:
            return True, "Files have changed"
        
        # Check age (regenerate if older than 1 hour)
        index_time = index.get("at", "")
        if index_time:
            try:
                dt = datetime.fromisoformat(index_time)
                age_minutes = (datetime.now() - dt).total_seconds() / 60
                if age_minutes > 60:
                    return True, f"Index is {int(age_minutes)} minutes old"
            except:
                pass
        
        return False, "Index is up to date"
    
    except Exception as e:
        return True, f"Error checking index: {e}"

def generate_index_at_size(project_root, target_size_k, is_clipboard_mode=False):
    """Generate index at specific token size."""
    print(f"🔍 Generating {'clipboard-optimized' if is_clipboard_mode else 'interactive'} index at ~{target_size_k}k tokens...", file=sys.stderr)
    
    # Calculate target bytes (rough estimate: 1 token ≈ 4 bytes)
    target_bytes = target_size_k * 1000 * 4
    
    # Build the index
    index, skipped = build_index(str(project_root))
    
    # Convert to dense format
    dense = convert_to_enhanced_dense_format(index)
    
    # Add metadata
    dense["last_interactive_size_k"] = target_size_k
    dense["files_hash"] = calculate_files_hash(project_root)
    dense["generated_for"] = "clipboard" if is_clipboard_mode else "interactive"
    
    # Compress if needed
    current_json = json.dumps(dense, separators=(',', ':'))
    current_size = len(current_json)
    
    if current_size > target_bytes:
        # Need compression
        print(f"📦 Compressing from {current_size//1000}k to {target_bytes//1000}k bytes...", file=sys.stderr)
        dense = compress_if_needed(dense, target_bytes)
    
    # Save the index
    index_path = project_root / "PROJECT_INDEX.json"
    with open(index_path, "w") as f:
        json.dump(dense, f, separators=(',', ':'))
    
    final_size = index_path.stat().st_size
    print(f"✅ Index generated: {final_size//1000}k bytes (~{final_size//4000}k tokens)", file=sys.stderr)
    
    return index_path

def copy_to_clipboard(prompt, index_path):
    """Copy prompt, instructions, and index to clipboard for external AI."""
    print("📋 Preparing clipboard content...", file=sys.stderr)
    
    # Load the index
    with open(index_path, "r") as f:
        index_content = f.read()
    
    # Clean the prompt of the -ic flag
    clean_prompt = re.sub(r'-ic?\s*\d*k?\s*', '', prompt).strip()
    
    # Create clipboard-specific instructions (no tools, no subagent references)
    clipboard_instructions = """You are analyzing a codebase index to help identify relevant files and code sections.

## YOUR TASK
Analyze the PROJECT_INDEX.json below to identify the most relevant code sections for the user's request.
The index contains file structures, function signatures, call graphs, and dependencies.

## WHAT TO LOOK FOR
- Identify specific files and functions related to the request
- Trace call graphs to understand code flow
- Note dependencies and relationships
- Consider architectural patterns

## IMPORTANT: RESPONSE FORMAT
Your response will be copied and pasted to Claude Code. Format your response as:

### 📍 RELEVANT CODE LOCATIONS

**Primary Files to Examine:**
- `path/to/file.py` - [Why relevant]
  - `function_name()` (line X) - [What it does]
  - Called by: [list any callers]
  - Calls: [list what it calls]

**Related Files:**
- `path/to/related.py` - [Connection to task]

### 🔍 KEY INSIGHTS
- [Architectural patterns observed]
- [Dependencies to consider]
- [Potential challenges or gotchas]

### 💡 RECOMMENDATIONS
- Start by examining: [specific file]
- Focus on: [specific functions/classes]
- Consider: [any special considerations]

Do NOT include the original user prompt in your response.
Focus on providing actionable file locations and insights."""
    
    # Build clipboard content
    clipboard_content = f"""# Codebase Analysis Request

## Task for You
{clean_prompt}

## Instructions
{clipboard_instructions}

## PROJECT_INDEX.json
{index_content}
"""
    
    # Copy to clipboard
    try:
        pyperclip.copy(clipboard_content)
        print(f"✅ Copied to clipboard: {len(clipboard_content)//1000}k bytes", file=sys.stderr)
        print("   Paste into your preferred AI assistant!", file=sys.stderr)
    except Exception as e:
        print(f"❌ Failed to copy to clipboard: {e}", file=sys.stderr)
        print("   You can manually copy from PROJECT_INDEX.json", file=sys.stderr)

def main():
    """Process UserPromptSubmit hook for -i and -ic flag detection."""
    try:
        # Read hook input from stdin (as per Claude Code hooks spec)
        input_data = json.load(sys.stdin)
        prompt = input_data.get('prompt', '')
        
        # Check for -i or -ic flag
        size_k, is_clipboard = parse_index_flag(prompt)
        
        if size_k is None:
            # No index flag found, let prompt proceed normally
            sys.exit(0)
        
        # Find project root
        project_root = find_project_root()
        index_path = project_root / "PROJECT_INDEX.json"
        
        # Check if we need to regenerate
        should_regen, reason = should_regenerate_index(project_root, index_path, size_k)
        
        if should_regen:
            print(f"🔄 Regenerating index: {reason}", file=sys.stderr)
            index_path = generate_index_at_size(project_root, size_k, is_clipboard)
        else:
            print(f"✨ Using existing index: {reason}", file=sys.stderr)
        
        # Clean the prompt (remove the -i/-ic flag)
        cleaned_prompt = re.sub(r'-i(c?)(\d+)?(?:\s|$)', '', prompt).strip()
        
        # Handle clipboard mode
        if is_clipboard:
            copy_to_clipboard(prompt, index_path)
            # For clipboard mode, we want to block the prompt and tell Claude not to process it
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"""
📋 Clipboard Mode Activated

Index and instructions copied to clipboard ({size_k}k tokens).
Paste into external AI (Gemini, Claude.ai, ChatGPT) for analysis.

**CRITICAL INSTRUCTION FOR CLAUDE**: STOP! Do NOT proceed with the original request. The user wants to use an external AI for analysis. You should:
1. ONLY acknowledge that the content was copied to clipboard
2. WAIT for the user to paste the external AI's response
3. DO NOT attempt to answer or work on: "{cleaned_prompt}"

Simply respond with: "✅ Index copied to clipboard for external AI analysis. Please paste the response here when ready."

User's request (DO NOT ANSWER): {cleaned_prompt}
"""
                }
            }
            print(json.dumps(output))
        else:
            # Standard mode - prepare for subagent analysis
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": f"""
## 🎯 Index-Aware Mode Activated

Generated/loaded {size_k}k token index at: {index_path}

**IMPORTANT**: You MUST use the index-analyzer subagent to analyze the codebase structure before proceeding with the request.

**How to invoke the subagent correctly**:
1. First say: "I'll analyze the codebase structure to understand the relevant code sections for your request."
2. Then invoke with the EXACT prompt:

Using the index-analyzer subagent to analyze the project:
- Read the PROJECT_INDEX.json file at: {index_path}
- User request: {cleaned_prompt}
- Provide analysis of relevant code sections, dependencies, and recommendations

**DO NOT** let the subagent search for PROJECT_INDEX.json - provide the exact path: {index_path}

The subagent will provide deep code intelligence including:
- Essential code paths and dependencies
- Call graphs and impact analysis
- Architectural insights and patterns
- Strategic recommendations

Original request (without -i flag): {cleaned_prompt}
"""
                }
            }
            print(json.dumps(output))
            
    except json.JSONDecodeError:
        # If we can't parse JSON, it means we're not being called as a hook
        print("Error: This script should be called as a Claude Code hook", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()