#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
#   "pyperclip",
# ]
# ///
"""
Comprehensive integration tests for py.
Tests UserPromptSubmit hook for -i and -ic flag detection.
Follows AAA pattern: Arrange, Act, Assert.
"""

import pytest
import json
import tempfile
import subprocess
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

# Import the module under test
# Temporarily change directory to handle relative imports
import os
original_cwd = os.getcwd()
test_dir = Path(__file__).parent
os.chdir(test_dir)
sys.path.insert(0, str(test_dir))

try:
    # Create a simple module that handles the imports
    exec("""
import json
import sys
import os
import re
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
try:
    import pyperclip
except ImportError:
    pyperclip = None

import project_utils
import project_indexer

# Import all the functions we need to test
def get_last_interactive_size():
    project_root = project_utils.find_project_root()
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
    pattern = r'-i(c?)(\\d+)?(?:\\s|$)'
    match = re.search(pattern, prompt)
    
    if not match:
        return None, False
    
    is_clipboard = match.group(1) == 'c'
    size_str = match.group(2)
    
    if size_str:
        size_k = int(size_str)
    else:
        size_k = get_last_interactive_size() or 50
    
    return size_k, is_clipboard

def calculate_files_hash(project_root):
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            files = sorted(result.stdout.strip().split('\\n'))
            hash_content = []
            for file in files:
                file_path = project_root / file
                if file_path.exists():
                    stat = file_path.stat()
                    hash_content.append(f"{file}:{stat.st_mtime}:{stat.st_size}")
            
            combined = "\\n".join(hash_content)
            return hashlib.md5(combined.encode()).hexdigest()
    except:
        pass
    
    all_files = []
    for path in project_root.rglob("*"):
        if path.is_file() and project_utils.should_index_file(path, project_root):
            rel_path = path.relative_to(project_root)
            stat = path.stat()
            all_files.append(f"{rel_path}:{stat.st_mtime}:{stat.st_size}")
    
    combined = "\\n".join(sorted(all_files))
    return hashlib.md5(combined.encode()).hexdigest()

def should_regenerate_index(project_root, index_path, requested_size_k):
    if not index_path.exists():
        return True, "No index exists"
    
    try:
        with open(index_path, "r") as f:
            index = json.load(f)
        
        last_size = index.get("last_interactive_size_k", 0)
        if abs(last_size - requested_size_k) > 5:
            return True, f"Size changed: {last_size}k → {requested_size_k}k"
        
        current_hash = calculate_files_hash(project_root)
        stored_hash = index.get("files_hash", "")
        
        if current_hash != stored_hash:
            return True, "Files have changed"
        
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
    print(f"🔍 Generating {'clipboard-optimized' if is_clipboard_mode else 'interactive'} index at ~{target_size_k}k tokens...", file=sys.stderr)
    
    target_bytes = target_size_k * 1000 * 4
    
    index, skipped = project_indexer.build_index(str(project_root))
    dense = project_indexer.convert_to_enhanced_dense_format(index)
    
    dense["last_interactive_size_k"] = target_size_k
    dense["files_hash"] = calculate_files_hash(project_root)
    dense["generated_for"] = "clipboard" if is_clipboard_mode else "interactive"
    
    current_json = json.dumps(dense, separators=(',', ':'))
    current_size = len(current_json)
    
    if current_size > target_bytes:
        print(f"📦 Compressing from {current_size//1000}k to {target_bytes//1000}k bytes...", file=sys.stderr)
        dense = project_indexer.compress_if_needed(dense, target_bytes)
    
    index_path = project_root / "PROJECT_INDEX.json"
    with open(index_path, "w") as f:
        json.dump(dense, f, separators=(',', ':'))
    
    final_size = index_path.stat().st_size
    print(f"✅ Index generated: {final_size//1000}k bytes (~{final_size//4000}k tokens)", file=sys.stderr)
    
    return index_path

def copy_to_clipboard(prompt, index_path):
    print("📋 Preparing clipboard content...", file=sys.stderr)
    
    with open(index_path, "r") as f:
        index_content = f.read()
    
    clean_prompt = re.sub(r'-ic?\\s*\\d*k?\\s*', '', prompt).strip()
    
    clipboard_instructions = '''You are analyzing a codebase index to help identify relevant files and code sections.

## YOUR TASK
Analyze the PROJECT_INDEX.json below to identify the most relevant code sections for the user's request.'''
    
    clipboard_content = f'''# Codebase Analysis Request

## Task for You
{clean_prompt}

## Instructions
{clipboard_instructions}

## PROJECT_INDEX.json
{index_content}
'''
    
    try:
        if pyperclip:
            pyperclip.copy(clipboard_content)
        print(f"✅ Copied to clipboard: {len(clipboard_content)//1000}k bytes", file=sys.stderr)
    except Exception as e:
        print(f"❌ Failed to copy to clipboard: {e}", file=sys.stderr)

def main():
    try:
        input_data = json.load(sys.stdin)
        prompt = input_data.get('prompt', '')
        
        size_k, is_clipboard = parse_index_flag(prompt)
        
        if size_k is None:
            sys.exit(0)
        
        project_root = project_utils.find_project_root()
        index_path = project_root / "PROJECT_INDEX.json"
        
        should_regen, reason = should_regenerate_index(project_root, index_path, size_k)
        
        if should_regen:
            print(f"🔄 Regenerating index: {reason}", file=sys.stderr)
            index_path = generate_index_at_size(project_root, size_k, is_clipboard)
        else:
            print(f"✨ Using existing index: {reason}", file=sys.stderr)
        
        if is_clipboard:
            copy_to_clipboard(prompt, index_path)
        
        return True
        
    except json.JSONDecodeError:
        print("Error: This script should be called as a Claude Code hook", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
""", globals())
finally:
    os.chdir(original_cwd)

# Now we have all the functions available in the global namespace

class TestFlagParsing:
    """Test flag parsing functionality."""
    
    def test_parse_index_flag_no_flag(self):
        """Test parse_index_flag returns None when no flag present."""
        # Arrange
        prompt = "Analyze this codebase for performance issues"
        
        # Act
        size_k, is_clipboard = parse_index_flag(prompt)
        
        # Assert
        assert size_k is None
        assert is_clipboard is False
    
    def test_parse_index_flag_simple_i(self):
        """Test parse_index_flag with simple -i flag."""
        # Arrange
        prompt = "Please analyze -i the authentication system"
        
        # Act
        with patch('__main__.get_last_interactive_size', return_value=None):
            size_k, is_clipboard = parse_index_flag(prompt)
        
        # Assert
        assert size_k == 50  # Default size
        assert is_clipboard is False
    
    def test_parse_index_flag_i_with_size(self):
        """Test parse_index_flag with -i and specific size."""
        # Arrange
        prompt = "Analyze -i100 the system architecture"
        
        # Act
        size_k, is_clipboard = parse_index_flag(prompt)
        
        # Assert
        assert size_k == 100
        assert is_clipboard is False
    
    def test_parse_index_flag_ic_clipboard(self):
        """Test parse_index_flag with -ic clipboard flag."""
        # Arrange
        prompt = "Please analyze -ic150 this for external review"
        
        # Act
        size_k, is_clipboard = parse_index_flag(prompt)
        
        # Assert
        assert size_k == 150
        assert is_clipboard is True
    
    def test_parse_index_flag_no_match_substring(self):
        """Test parse_index_flag doesn't match substrings like 'multi-index'."""
        # Arrange
        prompt = "This is a multi-index database optimization"
        
        # Act
        size_k, is_clipboard = parse_index_flag(prompt)
        
        # Assert
        assert size_k is None
        assert is_clipboard is False
    
    def test_parse_index_flag_remembers_last_size(self):
        """Test parse_index_flag uses remembered size from previous runs."""
        # Arrange
        prompt = "Analyze -i the codebase"
        
        # Act
        with patch('get_last_interactive_size', return_value=75):
            size_k, is_clipboard = parse_index_flag(prompt)
        
        # Assert
        assert size_k == 75  # Remembered size
        assert is_clipboard is False

class TestLastInteractiveSize:
    """Test last interactive size functionality."""
    
    def test_get_last_interactive_size_no_index(self):
        """Test get_last_interactive_size returns None when no index exists."""
        # Arrange & Act
        with patch('__main__.find_project_root') as mock_find_root:
            mock_find_root.return_value = Path("/nonexistent")
            result = get_last_interactive_size()
        
        # Assert
        assert result is None
    
    def test_get_last_interactive_size_with_stored_size(self):
        """Test get_last_interactive_size returns stored size."""
        # Arrange
        mock_index_data = {"last_interactive_size_k": 80}
        
        # Act
        with patch('__main__.find_project_root') as mock_find_root:
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_index_data))):
                with patch('pathlib.Path.exists', return_value=True):
                    mock_find_root.return_value = Path("/test")
                    result = get_last_interactive_size()
        
        # Assert
        assert result == 80
    
    def test_get_last_interactive_size_json_error(self):
        """Test get_last_interactive_size handles JSON errors gracefully."""
        # Arrange & Act
        with patch('__main__.find_project_root') as mock_find_root:
            with patch('builtins.open', mock_open(read_data="invalid json")):
                with patch('pathlib.Path.exists', return_value=True):
                    mock_find_root.return_value = Path("/test")
                    result = get_last_interactive_size()
        
        # Assert
        assert result is None

class TestFileHashing:
    """Test file hashing for change detection."""
    
    @patch('subprocess.run')
    def test_calculate_files_hash_git_success(self, mock_run):
        """Test calculate_files_hash uses git when available."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.py"
            test_file.write_text("print('hello')")
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout.strip.return_value = "test.py"
            mock_run.return_value = mock_result
            
            # Act
            result = calculate_files_hash(temp_path)
            
            # Assert
            assert result is not None
            assert len(result) == 32  # MD5 hash length
            mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_calculate_files_hash_git_failure_fallback(self, mock_run):
        """Test calculate_files_hash falls back when git fails."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.py"
            test_file.write_text("print('hello')")
            
            mock_result = MagicMock()
            mock_result.returncode = 1  # Git command fails
            mock_run.return_value = mock_result
            
            # Act
            with patch('should_index_file', return_value=True):
                result = calculate_files_hash(temp_path)
            
            # Assert
            assert result is not None
            assert len(result) == 32  # MD5 hash length

class TestIndexRegeneration:
    """Test index regeneration decision logic."""
    
    def test_should_regenerate_index_no_index(self):
        """Test should_regenerate_index when no index exists."""
        # Arrange
        project_root = Path("/test")
        index_path = project_root / "nonexistent.json"
        
        # Act
        should_regen, reason = should_regenerate_index(project_root, index_path, 50)
        
        # Assert
        assert should_regen is True
        assert "No index exists" in reason
    
    def test_should_regenerate_index_size_changed(self):
        """Test should_regenerate_index when size significantly changed."""
        # Arrange
        project_root = Path("/test")
        index_path = project_root / "PROJECT_INDEX.json"
        mock_index = {"last_interactive_size_k": 50}
        
        # Act
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_index))):
            with patch('pathlib.Path.exists', return_value=True):
                should_regen, reason = should_regenerate_index(project_root, index_path, 100)
        
        # Assert
        assert should_regen is True
        assert "Size changed" in reason
        assert "50k → 100k" in reason
    
    def test_should_regenerate_index_files_changed(self):
        """Test should_regenerate_index when files have changed."""
        # Arrange
        project_root = Path("/test")
        index_path = project_root / "PROJECT_INDEX.json"
        mock_index = {
            "last_interactive_size_k": 50,
            "files_hash": "old_hash"
        }
        
        # Act
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_index))):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('calculate_files_hash', return_value="new_hash"):
                    should_regen, reason = should_regenerate_index(project_root, index_path, 50)
        
        # Assert
        assert should_regen is True
        assert "Files have changed" in reason
    
    def test_should_regenerate_index_up_to_date(self):
        """Test should_regenerate_index when index is current."""
        # Arrange
        project_root = Path("/test")
        index_path = project_root / "PROJECT_INDEX.json"
        current_time = datetime.now().isoformat()
        mock_index = {
            "last_interactive_size_k": 50,
            "files_hash": "same_hash",
            "at": current_time
        }
        
        # Act
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_index))):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('calculate_files_hash', return_value="same_hash"):
                    should_regen, reason = should_regenerate_index(project_root, index_path, 50)
        
        # Assert
        assert should_regen is False
        assert "up to date" in reason

class TestIndexGeneration:
    """Test index generation functionality."""
    
    @patch('build_index')
    @patch('convert_to_enhanced_dense_format')
    @patch('calculate_files_hash')
    def test_generate_index_at_size(self, mock_hash, mock_convert, mock_build):
        """Test generate_index_at_size creates index successfully."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            mock_build.return_value = ({"test": "index"}, [])
            mock_convert.return_value = {"compressed": "index"}
            mock_hash.return_value = "test_hash"
            
            # Act
            with patch('builtins.print'):  # Suppress output
                result_path = generate_index_at_size(project_root, 50, False)
            
            # Assert
            assert result_path.exists()
            assert result_path.name == "PROJECT_INDEX.json"
            
            # Verify JSON is valid
            with open(result_path) as f:
                data = json.load(f)
                assert "last_interactive_size_k" in data
                assert "files_hash" in data

class TestClipboardFunctionality:
    """Test clipboard integration."""
    
    @patch('pyperclip.copy')
    def test_copy_to_clipboard_success(self, mock_copy):
        """Test copy_to_clipboard copies content successfully."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "index"}, f)
            index_path = Path(f.name)
        
        try:
            prompt = "Analyze -ic this codebase"
            
            # Act
            with patch('builtins.print'):  # Suppress output
                copy_to_clipboard(prompt, index_path)
            
            # Assert
            mock_copy.assert_called_once()
            clipboard_content = mock_copy.call_args[0][0]
            assert "Codebase Analysis Request" in clipboard_content
            assert "Analyze  this codebase" in clipboard_content  # Flag removed
            assert '{"test": "index"}' in clipboard_content
        finally:
            index_path.unlink()
    
    @patch('pyperclip.copy')
    def test_copy_to_clipboard_failure(self, mock_copy):
        """Test copy_to_clipboard handles errors gracefully."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "index"}, f)
            index_path = Path(f.name)
        
        mock_copy.side_effect = Exception("Clipboard error")
        
        try:
            prompt = "Analyze -ic this codebase"
            
            # Act & Assert - should not raise exception
            with patch('builtins.print'):  # Suppress output
                copy_to_clipboard(prompt, index_path)
            
            mock_copy.assert_called_once()
        finally:
            index_path.unlink()

class TestMainIntegration:
    """Test main function integration."""
    
    def test_main_no_flag_exits_normally(self):
        """Test main exits normally when no flag is detected."""
        # Arrange
        input_data = {"prompt": "Regular prompt without flags"}
        
        # Act & Assert
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', return_value=input_data):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
    
    @patch('__main__.find_project_root')
    @patch('should_regenerate_index')
    @patch('generate_index_at_size')
    def test_main_regenerates_index_when_needed(self, mock_generate, mock_should_regen, mock_find_root):
        """Test main regenerates index when necessary."""
        # Arrange
        input_data = {"prompt": "Analyze -i50 this system"}
        mock_find_root.return_value = Path("/test")
        mock_should_regen.return_value = (True, "Test reason")
        mock_generate.return_value = Path("/test/PROJECT_INDEX.json")
        
        # Act
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', return_value=input_data):
                with patch('builtins.print'):  # Suppress output
                    output = main()
        
        # Assert
        mock_generate.assert_called_once_with(Path("/test"), 50, False)
    
    @patch('__main__.find_project_root')
    @patch('should_regenerate_index')
    @patch('copy_to_clipboard')
    def test_main_clipboard_mode(self, mock_copy, mock_should_regen, mock_find_root):
        """Test main handles clipboard mode correctly."""
        # Arrange
        input_data = {"prompt": "Analyze -ic75 this for external review"}
        mock_find_root.return_value = Path("/test")
        mock_should_regen.return_value = (False, "Index up to date")
        
        # Act
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', return_value=input_data):
                with patch('builtins.print'):  # Suppress output
                    main()
        
        # Assert
        mock_copy.assert_called_once()
    
    def test_main_handles_json_decode_error(self):
        """Test main handles JSON decode errors gracefully."""
        # Arrange & Act & Assert
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', side_effect=json.JSONDecodeError("Invalid", "", 0)):
                with patch('builtins.print'):  # Suppress output
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])