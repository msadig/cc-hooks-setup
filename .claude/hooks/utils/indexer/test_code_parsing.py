#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
# ]
# ///
"""
Comprehensive tests for code_parsing.py functions.
Follows AAA pattern: Arrange, Act, Assert.
"""

import pytest
import tempfile
from pathlib import Path

# Import the module under test
import code_parsing

class TestPythonParsing:
    """Test Python code parsing functionality."""
    
    def test_extract_python_signatures_simple_function(self):
        """Test extracting simple Python function signatures."""
        # Arrange
        content = '''
def hello_world():
    print("Hello, World!")

def add_numbers(a, b):
    return a + b

async def async_function(data):
    return await process(data)
'''
        
        # Act
        result = code_parsing.extract_python_signatures(content)
        
        # Assert
        assert 'functions' in result
        assert 'hello_world' in result['functions']
        assert result['functions']['hello_world']['signature'] == "()"
        
        assert 'add_numbers' in result['functions']
        assert result['functions']['add_numbers']['signature'] == "(a, b)"
        
        assert 'async_function' in result['functions']
        assert result['functions']['async_function']['signature'] == "async (data)"
    
    def test_extract_python_signatures_classes(self):
        """Test extracting Python class signatures."""
        # Arrange
        content = '''
class User:
    def __init__(self, name):
        self.name = name
    
    def get_name(self):
        return self.name

class AdminUser(User):
    def __init__(self, name, permissions):
        super().__init__(name)
        self.permissions = permissions
'''
        
        # Act
        result = code_parsing.extract_python_signatures(content)
        
        # Assert
        assert 'classes' in result
        assert 'User' in result['classes']
        assert result['classes']['User']['methods'] == {}
        assert 'line' in result['classes']['User']
        
        assert 'AdminUser' in result['classes']
        assert 'inherits' in result['classes']['AdminUser']
        assert 'User' in result['classes']['AdminUser']['inherits']
    
    def test_extract_python_signatures_imports(self):
        """Test extracting Python import statements."""
        # Arrange
        content = '''
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests as req
'''
        
        # Act
        result = code_parsing.extract_python_signatures(content)
        
        # Assert
        assert 'imports' in result
        assert 'os' in result['imports']
        assert 'sys' in result['imports']
        assert 'pathlib' in result['imports']
        assert 'datetime' in result['imports']
        assert 'typing' in result['imports']
        assert 'requests' in result['imports']

class TestJavaScriptParsing:
    """Test JavaScript/TypeScript code parsing functionality."""
    
    def test_extract_javascript_signatures_functions(self):
        """Test extracting JavaScript function signatures."""
        # Arrange
        content = '''
function regularFunction(param1, param2) {
    return param1 + param2;
}

export function exportedFunction() {
    return "exported";
}

const arrowFunction = (x, y) => {
    return x * y;
};

export const exportedArrow = async (data) => {
    return await process(data);
};
'''
        
        # Act
        result = code_parsing.extract_javascript_signatures(content)
        
        # Assert
        assert 'functions' in result
        assert 'regularFunction' in result['functions']
        assert result['functions']['regularFunction'] == "(param1, param2)"
        
        assert 'exportedFunction' in result['functions']
        assert result['functions']['exportedFunction'] == "()"
        
        assert 'arrowFunction' in result['functions']
        assert result['functions']['arrowFunction'] == "(x, y)"
        
        assert 'exportedArrow' in result['functions']
        assert "async" in result['functions']['exportedArrow']
    
    def test_extract_javascript_signatures_classes(self):
        """Test extracting JavaScript class signatures."""
        # Arrange
        content = '''
class User {
    constructor(name) {
        this.name = name;
    }
    
    getName() {
        return this.name;
    }
}

export class AdminUser extends User {
    constructor(name, role) {
        super(name);
        this.role = role;
    }
}
'''
        
        # Act
        result = code_parsing.extract_javascript_signatures(content)
        
        # Assert
        assert 'classes' in result
        assert 'User' in result['classes']
        assert result['classes']['User']['methods'] == {}
        
        assert 'AdminUser' in result['classes']
        assert 'extends' in result['classes']['AdminUser']
        assert result['classes']['AdminUser']['extends'] == 'User'
    
    def test_extract_javascript_signatures_imports(self):
        """Test extracting JavaScript import statements."""
        # Arrange
        content = '''
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import axios from 'axios';
'''
        
        # Act
        result = code_parsing.extract_javascript_signatures(content)
        
        # Assert
        assert 'imports' in result
        assert 'react' in result['imports']
        assert './utils' in result['imports']
        assert 'axios' in result['imports']

class TestShellParsing:
    """Test shell script parsing functionality."""
    
    def test_extract_shell_signatures_functions(self):
        """Test extracting shell function signatures."""
        # Arrange
        content = '''#!/bin/bash

# This is a helper function
setup_environment() {
    export PATH="$PATH:$1"
    echo "Environment setup complete"
}

function validate_input {
    if [ -z "$1" ]; then
        echo "Error: No input provided"
        return 1
    fi
    echo "Input is valid: $1"
}

deploy() {
    setup_environment "/usr/local/bin"
    validate_input "$1"
    echo "Deploying $1 to production"
}
'''
        
        # Act
        result = code_parsing.extract_shell_signatures(content)
        
        # Assert
        assert 'functions' in result
        assert 'setup_environment' in result['functions']
        assert 'validate_input' in result['functions']
        assert 'deploy' in result['functions']
        
        # Check function with parameters
        setup_func = result['functions']['setup_environment']
        assert 'signature' in setup_func
        assert '${1}' in setup_func['signature']
        
        # Check function with docstring
        assert 'doc' in setup_func
        assert 'helper function' in setup_func['doc']
    
    def test_extract_shell_signatures_variables(self):
        """Test extracting shell variable declarations."""
        # Arrange
        content = '''#!/bin/bash

export DATABASE_URL="postgresql://localhost/mydb"
export DEBUG_MODE="true"

LOG_LEVEL="info"
MAX_RETRIES=5
'''
        
        # Act
        result = code_parsing.extract_shell_signatures(content)
        
        # Assert
        assert 'exports' in result
        assert 'DATABASE_URL' in result['exports']
        assert result['exports']['DATABASE_URL'] == 'str'
        assert 'DEBUG_MODE' in result['exports']
        
        assert 'variables' in result
        assert 'LOG_LEVEL' in result['variables']
        assert 'MAX_RETRIES' in result['variables']
    
    def test_extract_shell_signatures_sources(self):
        """Test extracting shell source/dot includes."""
        # Arrange
        content = '''#!/bin/bash

source /etc/profile
. ~/.bashrc
source "${HOME}/.config/shell/aliases"
'''
        
        # Act
        result = code_parsing.extract_shell_signatures(content)
        
        # Assert
        assert 'sources' in result
        assert '/etc/profile' in result['sources']
        assert '~/.bashrc' in result['sources']
        assert '${HOME}/.config/shell/aliases' in result['sources']

class TestSwiftParsing:
    """Test Swift code parsing functionality."""
    
    def test_extract_swift_signatures_functions(self):
        """Test extracting Swift function signatures."""
        # Arrange
        content = '''
public func publicFunction(param1: String, param2: Int) -> Bool {
    return true
}

private func privateHelper() {
    print("Helper")
}

func calculateSum<T: Numeric>(values: [T]) -> T {
    return values.reduce(0, +)
}
'''
        
        # Act
        result = code_parsing.extract_swift_signatures(content)
        
        # Assert
        assert 'functions' in result
        assert 'publicFunction' in result['functions']
        assert 'privateHelper' in result['functions']
        assert 'calculateSum' in result['functions']
        
        public_func = result['functions']['publicFunction']
        assert 'signature' in public_func
        assert 'Bool' in public_func['signature']
    
    def test_extract_swift_signatures_classes_structs(self):
        """Test extracting Swift classes and structs."""
        # Arrange
        content = '''
public class User: NSObject, Codable {
    let name: String
    let age: Int
}

struct Point: Equatable {
    let x: Double
    let y: Double
}

enum Status: String, CaseIterable {
    case active = "active"
    case inactive = "inactive"
}

protocol Drawable {
    func draw()
}

extension String {
    func trimmed() -> String {
        return self.trimmingCharacters(in: .whitespaces)
    }
}
'''
        
        # Act
        result = code_parsing.extract_swift_signatures(content)
        
        # Assert
        assert 'classes' in result
        assert 'User' in result['classes']
        assert 'inherits' in result['classes']['User']
        assert 'NSObject' in result['classes']['User']['inherits']
        
        assert 'structs' in result
        assert 'Point' in result['structs']
        
        assert 'enums' in result
        assert 'Status' in result['enums']
        
        assert 'protocols' in result
        assert 'Drawable' in result['protocols']
        
        assert 'extensions' in result
        assert 'String' in result['extensions']

class TestMarkdownParsing:
    """Test Markdown structure extraction functionality."""
    
    def test_extract_markdown_structure_headers(self):
        """Test extracting headers from markdown content."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('''# Main Title

## Getting Started

### Prerequisites

Some content here.

## API Reference

### Authentication

### Endpoints

#### GET /users

More content.

## Contributing

End of document.
''')
            md_path = Path(f.name)
        
        try:
            # Act
            result = code_parsing.extract_markdown_structure(md_path)
            
            # Assert
            assert 'sections' in result
            sections = result['sections']
            assert 'Main Title' in sections
            assert 'Getting Started' in sections
            assert 'Prerequisites' in sections
            assert 'API Reference' in sections
            assert 'Authentication' in sections
            assert len(sections) <= 10  # Should limit to 10 sections
        finally:
            md_path.unlink()
    
    def test_extract_markdown_structure_architecture_hints(self):
        """Test extracting architectural hints from markdown content."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('''# Project Structure

The main configuration is located in `config/settings.py`.

Authentication logic can be found in `auth/handlers.py`.

See `utils/database.py` for database utilities.

Check the `models/user.py` file for user model definition.
''')
            md_path = Path(f.name)
        
        try:
            # Act
            result = code_parsing.extract_markdown_structure(md_path)
            
            # Assert
            assert 'architecture_hints' in result
            hints = result['architecture_hints']
            assert any('config/settings.py' in hint for hint in hints)
            assert any('auth/handlers.py' in hint for hint in hints)
            assert any('utils/database.py' in hint for hint in hints)
        finally:
            md_path.unlink()
    
    def test_extract_markdown_structure_empty_file(self):
        """Test extracting structure from empty markdown file."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('')
            md_path = Path(f.name)
        
        try:
            # Act
            result = code_parsing.extract_markdown_structure(md_path)
            
            # Assert
            assert result == {'sections': [], 'architecture_hints': []}
        finally:
            md_path.unlink()

class TestFunctionCallExtraction:
    """Test function call extraction from different languages."""
    
    def test_extract_function_calls_python(self):
        """Test extracting Python function calls."""
        # Arrange
        body = '''
x = calculate_sum(a, b)
result = process_data(x)
self.validate_input(data)
obj.method_call(params)
'''
        all_functions = {'calculate_sum', 'process_data', 'validate_input', 'method_call'}
        
        # Act
        result = code_parsing.extract_function_calls_python(body, all_functions)
        
        # Assert
        assert 'calculate_sum' in result
        assert 'process_data' in result
        assert 'validate_input' in result
        assert 'method_call' in result
        assert result == sorted(result)  # Should be sorted
    
    def test_extract_function_calls_javascript(self):
        """Test extracting JavaScript function calls."""
        # Arrange
        body = '''
const result = processData(input);
this.validateInput(data);
utils.helper(params);
callback();
'''
        all_functions = {'processData', 'validateInput', 'helper', 'callback'}
        
        # Act
        result = code_parsing.extract_function_calls_javascript(body, all_functions)
        
        # Assert
        assert 'processData' in result
        assert 'validateInput' in result
        assert 'helper' in result
        assert 'callback' in result
    
    def test_extract_function_calls_shell(self):
        """Test extracting shell function calls."""
        # Arrange
        body = '''
setup_environment "/usr/local"
validate_input "$1" && deploy_app
result=$(get_config)
'''
        all_functions = {'setup_environment', 'validate_input', 'deploy_app', 'get_config'}
        
        # Act
        result = code_parsing.extract_function_calls_shell(body, all_functions)
        
        # Assert
        assert 'setup_environment' in result
        assert 'validate_input' in result
        assert 'get_config' in result

class TestCallGraphBuilding:
    """Test call graph construction functionality."""
    
    def test_build_call_graph_simple(self):
        """Test building call graph from function definitions."""
        # Arrange
        functions = {
            'main': {'calls': ['helper', 'validate']},
            'helper': {'calls': ['utility']},
            'validate': {'calls': []},
            'utility': {'calls': []}
        }
        classes = {}
        
        # Act
        calls_map, called_by_map = code_parsing.build_call_graph(functions, classes)
        
        # Assert
        assert 'main' in calls_map
        assert calls_map['main'] == ['helper', 'validate']
        
        assert 'helper' in called_by_map
        assert 'main' in called_by_map['helper']
        
        assert 'validate' in called_by_map
        assert 'main' in called_by_map['validate']
    
    def test_build_call_graph_with_classes(self):
        """Test building call graph including class methods."""
        # Arrange
        functions = {
            'main': {'calls': ['UserService.create_user']}
        }
        classes = {
            'UserService': {
                'methods': {
                    'create_user': {'calls': ['validate_email']},
                    'validate_email': {'calls': []}
                }
            }
        }
        
        # Act
        calls_map, called_by_map = code_parsing.build_call_graph(functions, classes)
        
        # Assert
        assert 'UserService.create_user' in calls_map
        assert calls_map['UserService.create_user'] == ['validate_email']
        
        assert 'UserService.create_user' in called_by_map
        assert 'main' in called_by_map['UserService.create_user']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])