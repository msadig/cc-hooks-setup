#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
# ]
# ///
"""
Comprehensive tests for project_utils.py utilities.
Follows AAA pattern: Arrange, Act, Assert.
"""

import pytest
import tempfile
import subprocess
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the module under test
import project_utils

class TestProjectDiscovery:
    """Test project root discovery functions."""
    
    def test_find_project_root_with_claude_project_dir(self):
        """Test find_project_root uses CLAUDE_PROJECT_DIR when available."""
        # Arrange
        test_path = "/test/project/path"
        
        # Act & Assert
        with patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': test_path}):
            result = project_utils.find_project_root()
            assert result == Path(test_path)
    
    def test_find_project_root_searches_for_markers(self):
        """Test find_project_root searches up directory tree for markers."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested structure
            nested_dir = temp_path / "subdir" / "deeper"
            nested_dir.mkdir(parents=True)
            
            # Create a .git directory in parent
            (temp_path / ".git").mkdir()
            
            # Act
            with patch('pathlib.Path.cwd', return_value=nested_dir):
                with patch.dict(os.environ, {}, clear=True):
                    result = project_utils.find_project_root()
            
            # Assert
            assert result == temp_path
    
    def test_find_project_root_fallback_to_cwd(self):
        """Test find_project_root falls back to current directory."""
        # Arrange
        mock_cwd = Path("/fallback/path")
        
        # Act & Assert
        with patch('pathlib.Path.cwd', return_value=mock_cwd):
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(Path, 'exists', return_value=False):
                    result = project_utils.find_project_root()
                    assert result == mock_cwd

class TestFileUtilities:
    """Test file analysis and filtering utilities."""
    
    def test_get_language_name_known_extension(self):
        """Test get_language_name returns correct language for known extensions."""
        # Arrange & Act & Assert
        assert project_utils.get_language_name('.py') == 'python'
        assert project_utils.get_language_name('.js') == 'javascript'
        assert project_utils.get_language_name('.swift') == 'swift'
    
    def test_get_language_name_unknown_extension(self):
        """Test get_language_name handles unknown extensions."""
        # Arrange & Act & Assert
        assert project_utils.get_language_name('.unknown') == 'unknown'
        assert project_utils.get_language_name('') == 'unknown'
    
    def test_infer_file_purpose_entry_points(self):
        """Test infer_file_purpose identifies entry point files."""
        # Arrange & Act & Assert
        assert project_utils.infer_file_purpose(Path("main.py")) == 'Application entry point'
        assert project_utils.infer_file_purpose(Path("index.js")) == 'Application entry point'
        assert project_utils.infer_file_purpose(Path("app.py")) == 'Application entry point'
    
    def test_infer_file_purpose_test_files(self):
        """Test infer_file_purpose identifies test files."""
        # Arrange & Act & Assert
        assert project_utils.infer_file_purpose(Path("test_main.py")) == 'Test file'
        assert project_utils.infer_file_purpose(Path("user.spec.js")) == 'Test file'
    
    def test_infer_file_purpose_unknown(self):
        """Test infer_file_purpose returns None for unknown files."""
        # Arrange & Act & Assert
        assert project_utils.infer_file_purpose(Path("random.py")) is None
    
    def test_should_index_file_code_extensions(self):
        """Test should_index_file accepts code file extensions."""
        # Arrange & Act & Assert
        assert project_utils.should_index_file(Path("test.py")) is True
        assert project_utils.should_index_file(Path("test.js")) is True
        assert project_utils.should_index_file(Path("README.md")) is True
    
    def test_should_index_file_ignored_extensions(self):
        """Test should_index_file rejects unsupported extensions."""
        # Arrange & Act & Assert
        assert project_utils.should_index_file(Path("test.exe")) is False
        assert project_utils.should_index_file(Path("test.bin")) is False
    
    def test_should_index_file_ignored_directories(self):
        """Test should_index_file rejects files in ignored directories."""
        # Arrange & Act & Assert
        assert project_utils.should_index_file(Path("node_modules/test.js")) is False
        assert project_utils.should_index_file(Path(".git/config")) is False
        assert project_utils.should_index_file(Path("__pycache__/test.py")) is False

class TestGitUtilities:
    """Test Git-related utility functions."""
    
    @patch('subprocess.run')
    def test_get_username_from_git_config(self, mock_run):
        """Test get_username retrieves name from git config."""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout.strip.return_value = "Test User"
        mock_run.return_value = mock_result
        
        # Act
        result = project_utils.get_username()
        
        # Assert
        assert result == "testuser"  # Should be lowercased and spaces removed
        mock_run.assert_called_once_with(
            ['git', 'config', 'user.name'],
            capture_output=True,
            text=True,
            check=False
        )
    
    @patch('subprocess.run')
    def test_get_username_fallback_to_env(self, mock_run):
        """Test get_username falls back to environment USER variable."""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1  # Git command fails
        mock_run.return_value = mock_result
        
        # Act & Assert
        with patch.dict(os.environ, {'USER': 'envuser'}):
            result = project_utils.get_username()
            assert result == 'envuser'
    
    @patch('subprocess.run')
    def test_get_git_info_success(self, mock_run):
        """Test get_git_info retrieves branch and status successfully."""
        # Arrange
        def mock_run_side_effect(cmd, **kwargs):
            result = MagicMock()
            if 'branch' in cmd:
                result.returncode = 0
                result.stdout.strip.return_value = "main"
            elif 'status' in cmd:
                result.returncode = 0
                result.stdout.strip.return_value = "M  test.py\nA  new.py"
            return result
        
        mock_run.side_effect = mock_run_side_effect
        
        # Act
        branch, status = project_utils.get_git_info()
        
        # Assert
        assert branch == "main"
        assert status == "M  test.py\nA  new.py"
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_get_git_info_failure(self, mock_run):
        """Test get_git_info handles command failures gracefully."""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        # Act
        branch, status = project_utils.get_git_info()
        
        # Assert
        assert branch == "unknown"
        assert status == ""
    
    @patch('subprocess.run')
    def test_get_git_files_success(self, mock_run):
        """Test get_git_files returns list of tracked files."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some test files
            (temp_path / "test1.py").touch()
            (temp_path / "test2.js").touch()
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout.strip.return_value = "test1.py\ntest2.js"
            mock_run.return_value = mock_result
            
            # Act
            result = project_utils.get_git_files(temp_path)
            
            # Assert
            assert result is not None
            assert len(result) == 2
            assert temp_path / "test1.py" in result
            assert temp_path / "test2.js" in result

class TestFileTracking:
    """Test file modification tracking utilities."""
    
    def test_format_time_ago_seconds(self):
        """Test format_time_ago for recent timestamps."""
        # Arrange
        time_delta = timedelta(seconds=30)
        
        # Act & Assert
        assert project_utils.format_time_ago(time_delta) == "just now"
    
    def test_format_time_ago_minutes(self):
        """Test format_time_ago for minute-level timestamps."""
        # Arrange
        time_delta = timedelta(minutes=5)
        
        # Act & Assert
        assert project_utils.format_time_ago(time_delta) == "5 minutes ago"
    
    def test_format_time_ago_hours(self):
        """Test format_time_ago for hour-level timestamps."""
        # Arrange
        time_delta = timedelta(hours=2.5)
        
        # Act & Assert
        result = project_utils.format_time_ago(time_delta)
        assert "2.5 hours ago" in result or "2 hours ago" in result
    
    def test_is_project_worth_indexing_sufficient_files(self):
        """Test is_project_worth_indexing returns True for projects with enough code files."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple code files
            for i in range(6):
                (temp_path / f"test{i}.py").touch()
            
            # Act
            result = project_utils.is_project_worth_indexing(temp_path)
            
            # Assert
            assert result is True
    
    def test_is_project_worth_indexing_insufficient_files(self):
        """Test is_project_worth_indexing returns False for small projects."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create only a few files
            (temp_path / "test1.py").touch()
            (temp_path / "test2.txt").touch()  # Non-code file
            
            # Act
            result = project_utils.is_project_worth_indexing(temp_path)
            
            # Assert
            assert result is False
    
    def test_get_index_age_existing_file(self):
        """Test get_index_age returns age for existing index file."""
        # Arrange
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
            try:
                # Act
                result = project_utils.get_index_age(temp_path)
                
                # Assert
                assert result is not None
                assert result >= 0  # Should be a small positive number (hours)
                assert result < 1   # Should be less than 1 hour old
            finally:
                temp_path.unlink()
    
    def test_get_index_age_nonexistent_file(self):
        """Test get_index_age returns None for nonexistent file."""
        # Arrange
        nonexistent_path = Path("/nonexistent/file.json")
        
        # Act & Assert
        assert project_utils.get_index_age(nonexistent_path) is None

class TestGitignoreHandling:
    """Test gitignore pattern matching functionality."""
    
    def test_parse_gitignore_valid_file(self):
        """Test parse_gitignore reads patterns from valid file."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gitignore', delete=False) as f:
            f.write("*.pyc\n")
            f.write("node_modules/\n")
            f.write("# Comment line\n")
            f.write("\n")  # Empty line
            f.write(".env\n")
            gitignore_path = Path(f.name)
        
        try:
            # Act
            result = project_utils.parse_gitignore(gitignore_path)
            
            # Assert
            assert "*.pyc" in result
            assert "node_modules/" in result
            assert ".env" in result
            assert "# Comment line" not in result  # Comments should be excluded
            assert "" not in result  # Empty lines should be excluded
        finally:
            gitignore_path.unlink()
    
    def test_parse_gitignore_nonexistent_file(self):
        """Test parse_gitignore handles nonexistent file gracefully."""
        # Arrange
        nonexistent_path = Path("/nonexistent/.gitignore")
        
        # Act & Assert
        assert project_utils.parse_gitignore(nonexistent_path) == []
    
    def test_matches_gitignore_pattern_simple_match(self):
        """Test matches_gitignore_pattern with simple patterns."""
        # Arrange
        patterns = {"*.pyc", "node_modules"}
        root_path = Path("/project")
        test_path = Path("/project/test.pyc")
        
        # Act & Assert
        assert project_utils.matches_gitignore_pattern(test_path, patterns, root_path) is True
    
    def test_matches_gitignore_pattern_no_match(self):
        """Test matches_gitignore_pattern with non-matching file."""
        # Arrange
        patterns = {"*.pyc", "node_modules"}
        root_path = Path("/project")
        test_path = Path("/project/test.py")
        
        # Act & Assert
        assert project_utils.matches_gitignore_pattern(test_path, patterns, root_path) is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])