#!/usr/bin/env python3
"""
Project and Git utilities for indexer_hook.py
Extracted from original utils.py for better organization.
"""

import os
import subprocess
import fnmatch
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Set

# ============================================================================
# CONSTANTS
# ============================================================================

# What to ignore (sensible defaults)
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env',
    'build', 'dist', '.next', 'target', '.pytest_cache', 'coverage',
    '.idea', '.vscode', '__pycache__', '.DS_Store', 'eggs', '.eggs',
    '.claude'  # Exclude Claude configuration directory
}

# Languages we can fully parse (extract functions/classes)
PARSEABLE_LANGUAGES = {
    '.py': 'python',
    '.js': 'javascript', 
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.sh': 'shell',
    '.bash': 'shell',
    '.swift': 'swift'
}

# All code file extensions we recognize
CODE_EXTENSIONS = {
    # Currently parsed
    '.py', '.js', '.ts', '.jsx', '.tsx', '.swift',
    # Common languages (listed but not parsed yet)
    '.go', '.rs', '.java', '.c', '.cpp', '.cc', '.cxx', 
    '.h', '.hpp', '.rb', '.php', '.kt', '.scala', 
    '.cs', '.sh', '.bash', '.sql', '.r', '.R', '.lua', '.m',
    '.ex', '.exs', '.jl', '.dart', '.vue', '.svelte',
    # Configuration and data files
    '.json', '.html', '.css'
}

# Markdown files to analyze
MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.rst'}

# Default limits (can be overridden by config)
MAX_FILES = 10000
MAX_INDEX_SIZE = 1024 * 1024  # 1MB
MAX_TREE_DEPTH = 5

# ============================================================================
# PROJECT UTILITIES
# ============================================================================

def find_project_root():
    """Find project root using CLAUDE_PROJECT_DIR or by looking for .git."""
    # First check environment variable
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])
    
    # Fall back to looking for project markers
    current = Path.cwd()
    markers = ['.git', 'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod']
    
    while current != current.parent:
        for marker in markers:
            if (current / marker).exists():
                return current
        current = current.parent
    
    return Path.cwd()

def load_project_config(project_root=None):
    """Load project-specific configuration from .indexconfig.yaml"""
    if project_root is None:
        project_root = os.getenv("CLAUDE_PROJECT_DIR", default=".")
    config_path = Path(project_root) / ".indexconfig.yaml"
    
    # Default configuration
    config = {
        'max_files': 10000,
        'max_index_size': 1024 * 1024,
        'max_tree_depth': 5,
        'ignore_dirs': set(IGNORE_DIRS),
        'parseable_languages': dict(PARSEABLE_LANGUAGES),
        'include_patterns': [],
        'exclude_patterns': [],
        'swift_support': False,
        'incremental': True,
        'compression_level': 'medium',
        'default_index_size': 50,
        'auto_regenerate_on_stop': True
    }
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                lines = f.readlines()
                for line in lines:
                    if ':' in line and not line.strip().startswith('#'):
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Parse common types
                        if value.lower() in ('true', 'false'):
                            config[key] = value.lower() == 'true'
                        elif value.isdigit():
                            config[key] = int(value)
                        else:
                            config[key] = value
        except Exception as e:
            print(f"⚠️  Error loading .indexconfig.yaml: {e}", file=os.sys.stderr)
    
    return config

def get_language_name(extension: str) -> str:
    """Get readable language name from extension."""
    if extension in PARSEABLE_LANGUAGES:
        return PARSEABLE_LANGUAGES[extension]
    return extension[1:] if extension else 'unknown'

def infer_file_purpose(file_path: Path) -> Optional[str]:
    """Infer the purpose of a file from its name and location."""
    name = file_path.stem.lower()
    
    if name in ['index', 'main', 'app']:
        return 'Application entry point'
    elif 'test' in name or 'spec' in name:
        return 'Test file'
    elif 'config' in name or 'settings' in name:
        return 'Configuration'
    elif 'route' in name:
        return 'Route definitions'
    elif 'model' in name:
        return 'Data model'
    elif 'util' in name or 'helper' in name:
        return 'Utility functions'
    elif 'middleware' in name:
        return 'Middleware'
    
    return None

def should_index_file(path: Path, root_path: Path = None) -> bool:
    """Check if we should index this file."""
    if not (path.suffix in CODE_EXTENSIONS or path.suffix in MARKDOWN_EXTENSIONS):
        return False
    
    for part in path.parts:
        if part in IGNORE_DIRS:
            return False
    
    if root_path:
        patterns = load_gitignore_patterns(root_path)
        if matches_gitignore_pattern(path, patterns, root_path):
            return False
    
    return True

# ============================================================================
# GITIGNORE UTILITIES
# ============================================================================

# Global cache for gitignore patterns
_gitignore_cache = {}

def parse_gitignore(gitignore_path: Path) -> List[str]:
    """Parse a .gitignore file and return list of patterns."""
    if not gitignore_path.exists():
        return []
    
    patterns = []
    try:
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                patterns.append(line)
    except:
        pass
    
    return patterns

def load_gitignore_patterns(root_path: Path) -> Set[str]:
    """Load all gitignore patterns from project root and merge with defaults."""
    cache_key = str(root_path)
    if cache_key in _gitignore_cache:
        return _gitignore_cache[cache_key]
    
    patterns = set(IGNORE_DIRS)
    
    gitignore_path = root_path / '.gitignore'
    if gitignore_path.exists():
        for pattern in parse_gitignore(gitignore_path):
            if not pattern.startswith('!'):
                patterns.add(pattern)
    
    _gitignore_cache[cache_key] = patterns
    return patterns

def matches_gitignore_pattern(path: Path, patterns: Set[str], root_path: Path) -> bool:
    """Check if a path matches any gitignore pattern."""
    try:
        rel_path = path.relative_to(root_path)
    except ValueError:
        return False
    
    path_str = str(rel_path)
    path_parts = rel_path.parts
    
    for pattern in patterns:
        clean_pattern = pattern.rstrip('/')
        for part in path_parts:
            if part == clean_pattern or fnmatch.fnmatch(part, clean_pattern):
                return True
        
        if '/' in pattern:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if pattern.startswith('/') and fnmatch.fnmatch(path_str, pattern[1:]):
                return True
        else:
            if fnmatch.fnmatch(path.name, pattern):
                return True
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(path_str, f'**/{pattern}'):
                return True
    
    return False

def get_git_files(root_path: Path) -> Optional[List[Path]]:
    """Get list of files tracked by git (respects .gitignore)."""
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            cwd=str(root_path),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            files = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    file_path = root_path / line
                    if file_path.is_file():
                        files.append(file_path)
            return files
        else:
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None

# ============================================================================
# GIT UTILITIES
# ============================================================================

def get_username():
    """Get username from git config or system environment."""
    try:
        result = subprocess.run(
            ['git', 'config', 'user.name'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            username = result.stdout.strip().replace(' ', '-').lower()
            username = username.replace('-', '')
            return username
    except Exception:
        pass
    
    return os.environ.get('USER', 'unknown')

def get_git_info():
    """Get current git branch and status."""
    try:
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=False
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'
        
        status_result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            check=False
        )
        status = status_result.stdout.strip() if status_result.returncode == 0 else ''
        
        return branch, status
    except Exception:
        return 'unknown', ''

# ============================================================================
# FILE TRACKING UTILITIES
# ============================================================================

def find_recent_files(project_root, hours=4):
    """Find files modified in the last N hours."""
    IGNORED_FOLDERS = [
        'node_modules', '__pycache__', '.git', '.venv', 'venv', 'env',
        'dist', 'build', 'target', '.pytest_cache', '.mypy_cache',
        '.tox', 'coverage', 'htmlcov', '.eggs', '*.egg-info', 'logs',
        '.next', '.nuxt', '.cache', 'tmp', 'temp', '.idea', '.vscode',
        'vendor', 'bower_components'
    ]
    
    recent_files = []
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    for file_path in project_root.rglob('*'):
        if any(part.startswith('.') for part in file_path.parts[1:]):
            continue
        
        path_parts = file_path.relative_to(project_root).parts
        if any(folder in path_parts for folder in IGNORED_FOLDERS):
            continue
        
        if not file_path.is_file():
            continue
        
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime > cutoff_time:
                time_ago = datetime.now() - mtime
                rel_path = file_path.relative_to(project_root)
                recent_files.append((str(rel_path), time_ago))
        except Exception:
            continue
    
    recent_files.sort(key=lambda x: x[1])
    return recent_files

def format_time_ago(time_delta):
    """Format a timedelta as a human-readable string."""
    total_seconds = time_delta.total_seconds()
    
    if total_seconds < 60:
        return "just now"
    elif total_seconds < 3600:
        minutes = int(total_seconds / 60)
        return f"{minutes} minutes ago" if minutes > 1 else "1 minute ago"
    else:
        hours = total_seconds / 3600
        if hours < 2:
            return f"{hours:.1f} hours ago"
        else:
            return f"{int(hours)} hours ago"

def is_project_worth_indexing(project_root):
    """Check if the project has enough code files to warrant indexing."""
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', 
                      '.rs', '.go', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.m'}
    
    code_file_count = 0
    try:
        for path in project_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in code_extensions:
                if any(part.startswith('.') for part in path.parts):
                    continue
                if 'node_modules' in path.parts or 'venv' in path.parts:
                    continue
                code_file_count += 1
                if code_file_count >= 5:
                    return True
    except:
        pass
    
    return False

def get_index_age(index_path):
    """Get the age of the index file in hours."""
    if not index_path.exists():
        return None
    
    try:
        stat = index_path.stat()
        age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
        return age.total_seconds() / 3600
    except:
        return None