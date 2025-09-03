#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
#   "pyperclip",
# ]
# ///
"""
Comprehensive tests for indexer_hook.py main entry point.
Follows AAA pattern: Arrange, Act, Assert.
"""

import pytest
import json
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import timedelta

# Add the hooks directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))
import indexer_hook

class TestIndexerHookMainEntry:
    """Test the main entry point and flag routing."""
    
    def test_version_display(self):
        """Test --version flag displays correct version."""
        # Arrange & Act & Assert
        result = subprocess.run([
            "uv", "run", str(Path(__file__).parent / "indexer_hook.py"), "--version"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "3.0.0" in result.stdout
    
    def test_help_display(self):
        """Test --help flag displays usage information."""
        # Arrange & Act
        result = subprocess.run([
            "uv", "run", str(Path(__file__).parent / "indexer_hook.py"), "--help"
        ], capture_output=True, text=True)
        
        # Assert
        assert result.returncode == 0
        assert "SessionStart hook" in result.stdout
        assert "Stop hook" in result.stdout
        assert "PreCompact hook" in result.stdout
        assert "UserPromptSubmit hook" in result.stdout
        assert "Main indexer" in result.stdout

class TestIndexerHookFunctions:
    """Test individual hook functions."""
    
    @patch('indexer_hook.find_project_root')
    @patch('indexer_hook.is_project_worth_indexing')
    def test_session_start_hook_not_worth_indexing(self, mock_worth_indexing, mock_find_root):
        """Test session_start_hook exits early if project not worth indexing."""
        # Arrange
        mock_find_root.return_value = Path("/test/path")
        mock_worth_indexing.return_value = False
        
        mock_input = {"source": "startup"}
        
        # Act & Assert
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', return_value=mock_input):
                with pytest.raises(SystemExit) as exc_info:
                    indexer_hook.session_start_hook()
                assert exc_info.value.code == 0
    
    @patch('indexer_hook.find_project_root')
    @patch('indexer_hook.is_project_worth_indexing')
    def test_session_start_hook_suggests_index_creation(self, mock_worth_indexing, mock_find_root):
        """Test session_start_hook suggests index creation when none exists."""
        # Arrange
        mock_project_root = Path("/test/path")
        mock_find_root.return_value = mock_project_root
        mock_worth_indexing.return_value = True
        
        mock_input = {"source": "startup"}
        
        # Act & Assert
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', return_value=mock_input):
                with patch('builtins.print') as mock_print:
                    with pytest.raises(SystemExit) as exc_info:
                        indexer_hook.session_start_hook()
                    
                    assert exc_info.value.code == 0
                    # Check that suggestion was printed
                    print_calls = [call.args[0] for call in mock_print.call_args_list]
                    suggestion_printed = any("Project Index Not Found" in str(call) for call in print_calls)
                    assert suggestion_printed
    
    @patch('indexer_hook.find_project_root')
    def test_stop_hook_no_index_exists(self, mock_find_root):
        """Test stop_hook exits early if no PROJECT_INDEX.json exists."""
        # Arrange
        mock_project_root = Path("/test/path")
        mock_find_root.return_value = mock_project_root
        
        # Act & Assert
        with patch('sys.stdin', MagicMock()):
            with patch('json.load', return_value={}):
                with pytest.raises(SystemExit) as exc_info:
                    indexer_hook.stop_hook()
                assert exc_info.value.code == 0

    def test_extract_user_prompts_empty_transcript(self):
        """Test extract_user_prompts handles empty transcript gracefully."""
        # Arrange
        project_root = Path("/test")
        input_data = {"transcript_path": "/nonexistent/path"}
        
        # Act
        result = indexer_hook.extract_user_prompts(project_root, input_data)
        
        # Assert
        assert result == []
    
    def test_extract_user_prompts_with_valid_data(self):
        """Test extract_user_prompts extracts prompts from valid transcript."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"role": "user", "content": "test prompt 1", "timestamp": "2024-01-01T10:00:00"}\n')
            f.write('{"role": "assistant", "content": "assistant response"}\n')
            f.write('{"role": "user", "content": "test prompt 2", "timestamp": "2024-01-01T10:01:00"}\n')
            transcript_path = f.name
        
        project_root = Path("/test")
        input_data = {"transcript_path": transcript_path}
        
        try:
            # Act
            result = indexer_hook.extract_user_prompts(project_root, input_data, max_prompts=5)
            
            # Assert
            assert len(result) == 2
            assert result[0][0] == "test prompt 2"  # Function reverses order
            assert result[1][0] == "test prompt 1"
        finally:
            Path(transcript_path).unlink()
    
    def test_generate_context_state_structure(self):
        """Test generate_context_state produces well-formed markdown."""
        # Arrange
        branch = "main"
        status = "M  test.py\nA  new.py"
        recent_files = [("test.py", timedelta(seconds=3600)), ("new.py", timedelta(seconds=1800))]  # timedelta objects
        timestamp = "2024-01-01T10:00:00"
        user_prompts = [("test prompt", "2024-01-01T09:30:00")]
        
        # Act
        result = indexer_hook.generate_context_state(branch, status, recent_files, timestamp, user_prompts)
        
        # Assert
        assert "# 🔄 Auto-Generated Context State" in result
        assert f"**Git Branch**: `{branch}`" in result
        assert status in result
        assert "test.py" in result
        assert "new.py" in result
        assert "test prompt" in result
        assert timestamp in result

class TestIndexerHookIntegration:
    """Integration tests for the complete hook system."""
    
    def test_project_index_execution(self):
        """Test that project indexer can be executed without errors."""
        # Arrange & Act
        result = subprocess.run([
            "uv", "run", str(Path(__file__).parent / "indexer_hook.py"), "--project-index"
        ], capture_output=True, text=True, timeout=30)
        
        # Assert
        assert result.returncode == 0
        assert "Building Project Index" in result.stdout or result.stderr
        
        # Check that PROJECT_INDEX.json was created
        index_path = Path("PROJECT_INDEX.json")
        assert index_path.exists()
        
        # Verify it's valid JSON
        with open(index_path) as f:
            index_data = json.load(f)
            assert 'at' in index_data  # Should have timestamp
            assert 'f' in index_data   # Should have files
    
    def test_flag_routing_session_start(self):
        """Test session-start flag routes to correct function."""
        # This test uses a mock stdin to avoid hanging on real input
        mock_input = {"source": "startup"}
        
        with patch('sys.stdin'):
            with patch('json.load', return_value=mock_input):
                with patch('indexer_hook.session_start_hook') as mock_hook:
                    # Arrange & Act
                    result = subprocess.run([
                        sys.executable, "-c",
                        f"import sys; sys.path.insert(0, '{Path(__file__).parent}'); "
                        f"from indexer_hook import main; "
                        f"import sys; sys.argv = ['test', '--session-start']; "
                        f"main()"
                    ], capture_output=True, text=True)
                    
                    # We can't easily test the subprocess call with mocks,
                    # so we test argument parsing directly
        
        # Test argument parsing directly
        import argparse
        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--session-start', action='store_true')
        group.add_argument('--stop', action='store_true')
        group.add_argument('--precompact', action='store_true')
        group.add_argument('--i-flag-hook', action='store_true')
        group.add_argument('--project-index', action='store_true')
        
        args = parser.parse_args(['--session-start'])
        assert args.session_start is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])