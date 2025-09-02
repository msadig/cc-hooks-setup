#!/usr/bin/env python3
"""
Comprehensive test suite for helper_hooks.py
Tests functionality, security, integration, and error handling.
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import time

# Add the hooks directory to the path so we can import helper_hooks
sys.path.insert(0, str(Path(__file__).parent))
import helper_hooks


class TestHelperHooks(unittest.TestCase):
    """Test suite for helper_hooks.py functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_claude_dir = helper_hooks.CLAUDE_PROJECT_DIR
        helper_hooks.CLAUDE_PROJECT_DIR = self.test_dir
        
        # Create test directories
        (self.test_dir / "logs").mkdir(exist_ok=True)
        (self.test_dir / ".claude").mkdir(exist_ok=True)
        (self.test_dir / "docs").mkdir(exist_ok=True)
        
        # Create test files
        self.create_test_files()
        
    def tearDown(self):
        """Clean up test environment."""
        helper_hooks.CLAUDE_PROJECT_DIR = self.original_claude_dir
        shutil.rmtree(self.test_dir)
    
    def create_test_files(self):
        """Create test files for context loading."""
        # Create test context files
        test_files = {
            ".claude/RULES.md": "# Test Rules\nThis is a test rules file.",
            ".claude/CONTEXT.md": "# Test Context\nThis is test context.",
            ".claude/TODO.md": "# Test TODO\n- [ ] Test item",
            "docs/MEMORY.md": "# Test Memory\nThis is test memory."
        }
        
        for file_path, content in test_files.items():
            full_path = self.test_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
    
    # ============================================================================
    # Common Functions Tests
    # ============================================================================
    
    def test_log_to_json(self):
        """Test JSON logging functionality."""
        test_data = {"test": "data", "timestamp": "2023-01-01"}
        helper_hooks.log_to_json("test_log", test_data)
        
        log_file = self.test_dir / "logs" / "test_log.json"
        self.assertTrue(log_file.exists())
        
        with open(log_file) as f:
            logged_data = json.load(f)
        
        self.assertEqual(len(logged_data), 1)
        self.assertEqual(logged_data[0], test_data)
        
        # Test appending to existing log
        test_data2 = {"test": "data2"}
        helper_hooks.log_to_json("test_log", test_data2)
        
        with open(log_file) as f:
            logged_data = json.load(f)
        
        self.assertEqual(len(logged_data), 2)
        self.assertEqual(logged_data[1], test_data2)
    
    def test_get_tts_script_path(self):
        """Test TTS script path resolution."""
        # Create mock TTS files
        tts_dir = self.test_dir / "utils" / "tts"
        tts_dir.mkdir(parents=True, exist_ok=True)
        
        elevenlabs_script = tts_dir / "elevenlabs_tts.py"
        openai_script = tts_dir / "openai_tts.py"
        pyttsx3_script = tts_dir / "pyttsx3_tts.py"
        
        # Test with no scripts available
        result = helper_hooks.get_tts_script_path()
        self.assertIsNone(result)
        
        # Test fallback to pyttsx3
        pyttsx3_script.touch()
        result = helper_hooks.get_tts_script_path()
        self.assertEqual(result, str(pyttsx3_script))
        
        # Test OpenAI priority with mock env var
        openai_script.touch()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            result = helper_hooks.get_tts_script_path()
            self.assertEqual(result, str(openai_script))
        
        # Test ElevenLabs highest priority
        elevenlabs_script.touch()
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test-key'}):
            result = helper_hooks.get_tts_script_path()
            self.assertEqual(result, str(elevenlabs_script))
    
    def test_get_llm_script_path(self):
        """Test LLM script path resolution."""
        # Create mock LLM files
        llm_dir = self.test_dir / "utils" / "llm"
        llm_dir.mkdir(parents=True, exist_ok=True)
        
        oai_script = llm_dir / "oai.py"
        anth_script = llm_dir / "anth.py"
        
        # Test with no scripts available
        result = helper_hooks.get_llm_script_path()
        self.assertIsNone(result)
        
        # Test Anthropic fallback
        anth_script.touch()
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            result = helper_hooks.get_llm_script_path()
            self.assertEqual(result, str(anth_script))
        
        # Test OpenAI priority
        oai_script.touch()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            result = helper_hooks.get_llm_script_path()
            self.assertEqual(result, str(oai_script))
    
    # ============================================================================
    # User Prompt Submit Tests
    # ============================================================================
    
    def test_validate_prompt_safe(self):
        """Test prompt validation with safe prompts."""
        safe_prompts = [
            "Hello, how are you?",
            "Please help me write some code",
            "Can you analyze this file?",
            "What is the weather like?"
        ]
        
        for prompt in safe_prompts:
            is_valid, reason = helper_hooks.validate_prompt(prompt)
            self.assertTrue(is_valid)
            self.assertIsNone(reason)
    
    def test_add_context_information(self):
        """Test context information loading."""
        context = helper_hooks.add_context_information()
        
        # Should contain content from test files
        self.assertIn("Test Rules", context)
        self.assertIn("Test Memory", context)
        self.assertIn(".claude/RULES.md", context)
        self.assertIn("docs/MEMORY.md", context)
    
    # ============================================================================
    # Session Start Tests
    # ============================================================================
    
    def test_get_git_status_no_repo(self):
        """Test git status when no repo exists."""
        result = helper_hooks.get_git_status()
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_get_git_status_with_repo(self, mock_run):
        """Test git status with mock git repository."""
        # Create .git directory
        (self.test_dir / ".git").mkdir()
        
        # Mock git commands
        mock_responses = [
            # git branch --show-current
            MagicMock(returncode=0, stdout="main\n"),
            # git rev-parse upstream
            MagicMock(returncode=0, stdout="origin/main\n"),
            # git rev-list ahead
            MagicMock(returncode=0, stdout="2\n"),
            # git rev-list behind
            MagicMock(returncode=0, stdout="1\n"),
            # git status --porcelain
            MagicMock(returncode=0, stdout="M  file1.py\n?? file2.py\nA  file3.py\n"),
            # git log
            MagicMock(returncode=0, stdout="abc1234 Latest commit message\n")
        ]
        mock_run.side_effect = mock_responses
        
        result = helper_hooks.get_git_status()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['branch'], 'main')
        self.assertEqual(result['upstream'], 'origin/main')
        self.assertEqual(result['ahead'], 2)
        self.assertEqual(result['behind'], 1)
        self.assertEqual(result['staged'], 1)  # A file3.py
        self.assertEqual(result['modified'], 1)  # M file1.py
        self.assertEqual(result['untracked'], 1)  # ?? file2.py
        self.assertEqual(result['total_changes'], 3)
        self.assertEqual(result['last_commit'], 'abc1234 Latest commit message')
    
    def test_load_development_context(self):
        """Test development context loading."""
        with patch.object(helper_hooks, 'get_git_status', return_value=None):
            context = helper_hooks.load_development_context("startup")
            
            # Should contain session start info
            self.assertIn("Session started at:", context)
            self.assertIn("Session source: startup", context)
            
            # Should contain context file content
            self.assertIn("Test Context", context)
            self.assertIn("Test TODO", context)
    
    # ============================================================================
    # Pre Tool Use Tests
    # ============================================================================
    
    def test_is_dangerous_rm_command(self):
        """Test dangerous rm command detection."""
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "rm -fr ~/",
            "rm -Rf .",
            "rm --recursive --force /home",
            "rm --force --recursive .",
            "rm -r -f ~",
            "rm -f -r .",
            "sudo rm -rf /",
            "  rm   -rf   /  ",  # Extra spaces
            "RM -RF /",  # Case variations
        ]
        
        safe_commands = [
            "rm file.txt",
            "rm -f file.txt",
            "rm -r directory",
            "rm *.tmp",
            "cp -rf source dest",
            "ls -rf",
            "find . -name '*.tmp' -exec rm {} \\;",
        ]
        
        for cmd in dangerous_commands:
            self.assertTrue(helper_hooks.is_dangerous_rm_command(cmd), 
                          f"Failed to detect dangerous command: {cmd}")
        
        for cmd in safe_commands:
            self.assertFalse(helper_hooks.is_dangerous_rm_command(cmd), 
                           f"False positive for safe command: {cmd}")
    
    def test_is_env_file_access(self):
        """Test .env file access detection."""
        # Test file-based tools
        self.assertTrue(helper_hooks.is_env_file_access("Read", {"file_path": ".env"}))
        self.assertTrue(helper_hooks.is_env_file_access("Edit", {"file_path": "/path/.env"}))
        self.assertTrue(helper_hooks.is_env_file_access("Write", {"file_path": "project/.env"}))
        
        # Test .env.sample is allowed
        self.assertFalse(helper_hooks.is_env_file_access("Read", {"file_path": ".env.sample"}))
        
        # Test bash commands
        bash_env_commands = [
            "cat .env",
            "echo 'API_KEY=test' > .env",
            "touch .env",
            "cp config.env .env",
            "mv temp.env .env",
        ]
        
        for cmd in bash_env_commands:
            self.assertTrue(helper_hooks.is_env_file_access("Bash", {"command": cmd}),
                          f"Failed to detect .env access in: {cmd}")
        
        # Test safe commands
        safe_commands = [
            "cat .env.sample",
            "echo 'test' > .env.sample",
            "ls -la",
            "cat README.md",
        ]
        
        for cmd in safe_commands:
            self.assertFalse(helper_hooks.is_env_file_access("Bash", {"command": cmd}),
                           f"False positive for safe command: {cmd}")
    
    # ============================================================================
    # Pre Compact Tests
    # ============================================================================
    
    def test_backup_transcript(self):
        """Test transcript backup functionality."""
        # Create a test transcript file
        transcript_content = {"test": "transcript", "data": "example"}
        transcript_path = self.test_dir / "transcript.json"
        with open(transcript_path, 'w') as f:
            json.dump(transcript_content, f)
        
        # Test backup
        backup_path = helper_hooks.backup_transcript(str(transcript_path), "limit")
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(Path(backup_path).exists())
        
        # Verify backup content
        with open(backup_path) as f:
            backup_content = json.load(f)
        
        self.assertEqual(backup_content, transcript_content)
        
        # Verify backup is in correct directory
        backup_dir = self.test_dir / "logs" / "transcript_backups"
        self.assertTrue(backup_dir.exists())
        self.assertTrue(Path(backup_path).name.startswith("transcript_limit_"))
    
    # ============================================================================
    # Integration Tests
    # ============================================================================
    
    def test_cli_interface(self):
        """Test command line interface integration."""
        # Test invalid hook type
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent / "helper_hooks.py"),
            "invalid_hook"
        ], capture_output=True, text=True, input="{}")
        self.assertNotEqual(result.returncode, 0)  # Should fail
        
        # Test valid hook type with JSON input
        test_input = {"session_id": "test", "source": "startup"}
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent / "helper_hooks.py"),
            "session_start"
        ], capture_output=True, text=True, input=json.dumps(test_input))
        self.assertEqual(result.returncode, 0)  # Should succeed
    
    def test_json_error_handling(self):
        """Test JSON error handling."""
        # Test with invalid JSON
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent / "helper_hooks.py"),
            "session_start"
        ], capture_output=True, text=True, input="invalid json")
        self.assertEqual(result.returncode, 0)  # Should handle gracefully
    
    # ============================================================================
    # Security Tests
    # ============================================================================
    
    def test_security_dangerous_rm_blocking(self):
        """Test that dangerous rm commands are blocked."""
        test_input = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"}
        }
        
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent / "helper_hooks.py"),
            "pre_tool_use"
        ], capture_output=True, text=True, input=json.dumps(test_input))
        
        self.assertEqual(result.returncode, 2)  # Should block with exit code 2
        self.assertIn("BLOCKED", result.stderr)
        self.assertIn("Dangerous rm command", result.stderr)
    
    def test_security_env_file_blocking(self):
        """Test that .env file access is blocked."""
        test_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": ".env"}
        }
        
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent / "helper_hooks.py"),
            "pre_tool_use"
        ], capture_output=True, text=True, input=json.dumps(test_input))
        
        self.assertEqual(result.returncode, 2)  # Should block with exit code 2
        self.assertIn("BLOCKED", result.stderr)
        self.assertIn("Access to .env file", result.stderr)
    
    def test_security_safe_operations(self):
        """Test that safe operations are allowed."""
        safe_inputs = [
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md"}
            },
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"}
            },
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "config.py", "old_string": "old", "new_string": "new"}
            }
        ]
        
        for test_input in safe_inputs:
            result = subprocess.run([
                sys.executable, str(Path(__file__).parent / "helper_hooks.py"),
                "pre_tool_use"
            ], capture_output=True, text=True, input=json.dumps(test_input))
            
            self.assertEqual(result.returncode, 0, f"Safe operation blocked: {test_input}")
    
    # ============================================================================
    # Performance Tests
    # ============================================================================
    
    def test_performance_logging(self):
        """Test performance of logging operations."""
        start_time = time.time()
        
        # Test rapid logging
        for i in range(100):
            helper_hooks.log_to_json("performance_test", {"iteration": i, "data": f"test_{i}"})
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete within reasonable time (2 seconds for 100 operations)
        self.assertLess(elapsed, 2.0, f"Logging performance too slow: {elapsed}s for 100 operations")
        
        # Verify all entries were logged
        log_file = self.test_dir / "logs" / "performance_test.json"
        with open(log_file) as f:
            logged_data = json.load(f)
        
        self.assertEqual(len(logged_data), 100)
    
    # ============================================================================
    # Error Handling Tests
    # ============================================================================
    
    def test_error_handling_missing_directories(self):
        """Test error handling when required directories are missing."""
        # Remove logs directory
        shutil.rmtree(self.test_dir / "logs", ignore_errors=True)
        
        # Should create directory automatically
        helper_hooks.log_to_json("test_missing_dir", {"test": "data"})
        
        log_file = self.test_dir / "logs" / "test_missing_dir.json"
        self.assertTrue(log_file.exists())
    
    def test_error_handling_corrupted_log_file(self):
        """Test error handling with corrupted log files."""
        log_file = self.test_dir / "logs" / "corrupted.json"
        
        # Create corrupted JSON file
        with open(log_file, 'w') as f:
            f.write("{invalid json content")
        
        # Should handle corruption gracefully and recreate
        helper_hooks.log_to_json("corrupted", {"test": "data"})
        
        with open(log_file) as f:
            logged_data = json.load(f)
        
        # Should contain only the new entry (old corrupted data discarded)
        self.assertEqual(len(logged_data), 1)
        self.assertEqual(logged_data[0], {"test": "data"})


def run_comprehensive_tests():
    """Run all tests and generate a report."""
    print("🧪 Starting Comprehensive Helper Hooks Analysis...")
    print("=" * 60)
    
    # Run the unittest suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHelperHooks)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n🚨 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Error:')[-1].strip()}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)