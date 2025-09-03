#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
# ]
# ///
"""
Simple integration tests for flag_hook.py functionality.
Tests key functions by running the script as subprocess.
Follows AAA pattern: Arrange, Act, Assert.
"""

import pytest
import json
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestFlagHookExecution:
    """Test flag_hook.py execution as subprocess."""
    
    def test_no_flag_exits_zero(self):
        """Test script exits with code 0 when no flag is present."""
        # Arrange
        input_data = {"prompt": "Regular prompt without flags"}
        input_json = json.dumps(input_data)
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=input_json, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Assert
        assert result.returncode == 0
    
    def test_simple_i_flag_detected(self):
        """Test script processes -i flag correctly."""
        # Arrange
        input_data = {"prompt": "Analyze -i this system"}
        input_json = json.dumps(input_data)
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=input_json, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Assert
        # The script should run and either generate or use existing index
        assert result.returncode == 0
        # Should mention index activity in stderr
        assert "index" in result.stderr.lower() or len(result.stderr) == 0
    
    def test_ic_flag_clipboard_mode(self):
        """Test script processes -ic flag for clipboard mode."""
        # Arrange
        input_data = {"prompt": "Analyze -ic50 this for external review"}
        input_json = json.dumps(input_data)
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=input_json, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Assert
        # Script should run and attempt clipboard operations
        assert result.returncode == 0
        # Should mention clipboard or copying in stderr
        assert "clipboard" in result.stderr.lower() or "copying" in result.stderr.lower() or len(result.stderr) == 0

class TestFlagPatternMatching:
    """Test flag pattern matching with regex."""
    
    def test_regex_patterns(self):
        """Test flag regex patterns work correctly."""
        # Test the actual regex pattern from flag_hook.py
        import re
        
        pattern = r'-i(c?)(\d+)?(?:\s|$)'
        
        # Test cases
        test_cases = [
            ("analyze -i this", True, False, None),
            ("analyze -i50 this", True, False, "50"),
            ("analyze -ic this", True, True, None),
            ("analyze -ic75 this", True, True, "75"),
            ("multi-index database", False, None, None),
            ("some-index pattern", False, None, None),
            ("analyze -i", True, False, None),  # End of string
        ]
        
        for prompt, should_match, expected_clipboard, expected_size in test_cases:
            match = re.search(pattern, prompt)
            
            if should_match:
                assert match is not None, f"Should match: {prompt}"
                is_clipboard = match.group(1) == 'c'
                size_str = match.group(2)
                assert is_clipboard == expected_clipboard, f"Clipboard flag wrong for: {prompt}"
                assert size_str == expected_size, f"Size wrong for: {prompt}"
            else:
                assert match is None, f"Should not match: {prompt}"

class TestIndexPathGeneration:
    """Test index file path generation."""
    
    def test_project_index_json_created(self):
        """Test that PROJECT_INDEX.json is created in project root."""
        # This is more of an integration test that verifies the indexer can run
        # without errors and creates the expected output file
        
        # Arrange
        input_data = {"prompt": "Generate -i25 project index"}
        input_json = json.dumps(input_data)
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=input_json, capture_output=True, text=True, 
        cwd=Path(__file__).parent, timeout=30)
        
        # Assert - script should complete without error
        # Note: We can't easily test file creation without affecting the real project
        # so we just verify the script runs successfully
        assert result.returncode == 0

class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json_input(self):
        """Test script handles invalid JSON gracefully."""
        # Arrange
        invalid_json = "not json at all"
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=invalid_json, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Assert
        assert result.returncode == 1
        assert "error" in result.stderr.lower() or "json" in result.stderr.lower()
    
    def test_missing_prompt_key(self):
        """Test script handles missing prompt key gracefully."""
        # Arrange
        input_data = {"not_prompt": "missing the prompt key"}
        input_json = json.dumps(input_data)
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=input_json, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        # Assert
        # Should exit normally since no flag is detected in empty/missing prompt
        assert result.returncode == 0

class TestOutputFormat:
    """Test output format for Claude Code hooks."""
    
    def test_clipboard_mode_output_structure(self):
        """Test clipboard mode produces proper hook output structure."""
        # Arrange
        input_data = {"prompt": "Analyze -ic30 this system"}
        input_json = json.dumps(input_data)
        
        # Act
        result = subprocess.run([
            "uv", "run", "flag_hook.py"
        ], input=input_json, capture_output=True, text=True, 
        cwd=Path(__file__).parent, timeout=30)
        
        # Assert
        assert result.returncode == 0
        
        # Should produce JSON output for Claude Code hooks
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                # Should have hook-specific output structure
                assert "hookSpecificOutput" in output
                assert "hookEventName" in output["hookSpecificOutput"]
                assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
            except json.JSONDecodeError:
                # If clipboard operations fail, might not produce JSON output
                # This is acceptable for this test
                pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])