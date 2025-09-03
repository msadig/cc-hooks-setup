#!/usr/bin/env python3
"""
Code parsing utilities for different programming languages.
Extracted from original indexer_hook.py for better organization.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

# ============================================================================
# CODE PARSING UTILITIES
# ============================================================================

def extract_swift_signatures(content: str) -> Dict[str, Any]:
    """Extract Swift function and class signatures."""
    result = {
        'functions': {},
        'classes': {},
        'structs': {},
        'enums': {},
        'protocols': {},
        'extensions': {}
    }
    
    lines = content.split('\n')
    
    # Simple regex patterns for Swift
    func_pattern = r'^\s*((?:public|private|internal|open|fileprivate)\s+)?func\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)(?:\s*->\s*([^{]+))?'
    class_pattern = r'^\s*((?:public|private|internal|open|fileprivate)\s+)?class\s+(\w+)(?:\s*:\s*([^{]+))?'
    struct_pattern = r'^\s*((?:public|private|internal|open|fileprivate)\s+)?struct\s+(\w+)(?:\s*:\s*([^{]+))?'
    enum_pattern = r'^\s*((?:public|private|internal|open|fileprivate)\s+)?enum\s+(\w+)(?:\s*:\s*([^{]+))?'
    protocol_pattern = r'^\s*((?:public|private|internal|open|fileprivate)\s+)?protocol\s+(\w+)(?:\s*:\s*([^{]+))?'
    extension_pattern = r'^\s*extension\s+(\w+)(?:\s*:\s*([^{]+))?'
    
    for i, line in enumerate(lines):
        # Functions
        match = re.match(func_pattern, line)
        if match:
            access, name, returns = match.groups()
            signature = f"() -> {returns.strip()}" if returns else "()"
            result['functions'][name] = {'signature': signature, 'line': i + 1}
        
        # Classes
        match = re.match(class_pattern, line)
        if match:
            access, name, inherits = match.groups()
            class_info = {'line': i + 1, 'methods': {}}
            if inherits:
                class_info['inherits'] = [x.strip() for x in inherits.split(',')]
            result['classes'][name] = class_info
        
        # Structs
        match = re.match(struct_pattern, line)
        if match:
            access, name, conforms = match.groups()
            struct_info = {'line': i + 1}
            if conforms:
                struct_info['conforms'] = [x.strip() for x in conforms.split(',')]
            result['structs'][name] = struct_info
        
        # Enums
        match = re.match(enum_pattern, line)
        if match:
            access, name, raw_type = match.groups()
            enum_info = {'line': i + 1, 'values': []}
            if raw_type:
                enum_info['raw_type'] = raw_type.strip()
            result['enums'][name] = enum_info
        
        # Protocols
        match = re.match(protocol_pattern, line)
        if match:
            access, name, inherits = match.groups()
            protocol_info = {'line': i + 1}
            if inherits:
                protocol_info['inherits'] = [x.strip() for x in inherits.split(',')]
            result['protocols'][name] = protocol_info
        
        # Extensions
        match = re.match(extension_pattern, line)
        if match:
            name, conforms = match.groups()
            ext_info = {'line': i + 1}
            if conforms:
                ext_info['conforms'] = [x.strip() for x in conforms.split(',')]
            if name not in result['extensions']:
                result['extensions'][name] = []
            result['extensions'][name].append(ext_info)
    
    # Clean up empty collections
    for key in list(result.keys()):
        if not result[key]:
            del result[key]
    
    return result

def extract_python_signatures(content: str) -> Dict[str, Dict]:
    """Extract Python function and class signatures (simplified version)."""
    result = {
        'imports': [],
        'functions': {}, 
        'classes': {}, 
        'constants': {}, 
        'variables': []
    }
    
    lines = content.split('\n')
    
    # Collect all function names for call detection
    all_function_names = set()
    for line in lines:
        func_match = re.match(r'^(?:[ \t]*)(async\s+)?def\s+(\w+)\s*\(', line)
        if func_match:
            all_function_names.add(func_match.group(2))
    
    # Extract imports
    import_pattern = r'^(?:from\s+([^\s]+)\s+)?import\s+(.+)$'
    for line in lines:
        import_match = re.match(import_pattern, line.strip())
        if import_match:
            module, items = import_match.groups()
            if module:
                result['imports'].append(module)
            else:
                for item in items.split(','):
                    item = item.strip().split(' as ')[0]
                    result['imports'].append(item)
    
    # Extract functions and classes (simplified)
    for i, line in enumerate(lines):
        # Functions
        func_match = re.match(r'^([ \t]*)(async\s+)?def\s+(\w+)\s*\((.*?)\)', line)
        if func_match:
            indent, is_async, name, params = func_match.groups()
            signature = f"({params})"
            if is_async:
                signature = "async " + signature
            result['functions'][name] = {'signature': signature, 'line': i + 1}
        
        # Classes
        class_match = re.match(r'^class\s+(\w+)(?:\s*\((.*?)\))?:', line)
        if class_match:
            name, bases = class_match.groups()
            class_info = {'methods': {}, 'line': i + 1}
            if bases:
                class_info['inherits'] = [b.strip() for b in bases.split(',')]
            result['classes'][name] = class_info
    
    return result

def extract_javascript_signatures(content: str) -> Dict[str, Any]:
    """Extract JavaScript/TypeScript function and class signatures (simplified)."""
    result = {
        'imports': [],
        'functions': {}, 
        'classes': {}, 
        'constants': {}
    }
    
    # Extract imports
    import_pattern = r'import\s+(?:([^{}\s]+)|{([^}]+)}|\*\s+as\s+(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(import_pattern, content):
        module = match.group(4)
        if module:
            result['imports'].append(module)
    
    # Extract functions
    func_patterns = [
        r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>'
    ]
    
    for pattern in func_patterns:
        for match in re.finditer(pattern, content):
            func_name = match.group(1)
            params = match.group(2) if match.lastindex >= 2 else ''
            signature = f"({params})"
            if 'async' in match.group(0):
                signature = "async " + signature
            result['functions'][func_name] = signature
    
    # Extract classes
    class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
    for match in re.finditer(class_pattern, content):
        class_name, extends = match.groups()
        class_info = {'methods': {}}
        if extends:
            class_info['extends'] = extends
        result['classes'][class_name] = class_info
    
    return result

def extract_shell_signatures(content: str) -> Dict[str, Any]:
    """Extract shell script function signatures and structure."""
    result = {
        'functions': {},
        'variables': [],
        'exports': {},
        'sources': [],
        'call_graph': {}
    }
    
    lines = content.split('\n')
    
    # First pass: collect all function names
    all_function_names = set()
    for line in lines:
        match1 = re.match(r'^(\w+)\s*\(\)\s*\{?', line)
        if match1:
            all_function_names.add(match1.group(1))
        match2 = re.match(r'^function\s+(\w+)\s*\{?', line)
        if match2:
            all_function_names.add(match2.group(1))
    
    # Function patterns
    func_pattern1 = r'^(\w+)\s*\(\)\s*\{?'
    func_pattern2 = r'^function\s+(\w+)\s*\{?'
    
    # Variable patterns
    export_pattern = r'^export\s+([A-Z_][A-Z0-9_]*)(=(.*))?'
    var_pattern = r'^([A-Z_][A-Z0-9_]*)=(.+)$'
    
    # Source patterns
    source_patterns = [
        r'^(?:source|\.)\s+([\'"])([^\'"]+)\1',
        r'^(?:source|\.)\s+(\$\([^)]+\)[^\s]*)',
        r'^(?:source|\.)\s+([^\s]+)',
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if not stripped or stripped.startswith('#!'):
            continue
            
        # Check for function definition (style 1)
        match = re.match(func_pattern1, stripped)
        if match:
            func_name = match.group(1)
            doc = None
            if i > 0 and lines[i-1].strip().startswith('#'):
                doc = lines[i-1].strip()[1:].strip()
            
            params = []
            for j in range(i+1, min(i+20, len(lines))):
                param_matches = re.findall(r'\$(\d+)', lines[j])
                for p in param_matches:
                    param_num = int(p)
                    if param_num > 0 and param_num not in params:
                        params.append(param_num)
            
            if params:
                max_param = max(params)
                param_list = ' '.join(f'${{{j}}}' for j in range(1, max_param + 1))
                signature = f"({param_list})"
            else:
                signature = "()"
            
            func_info = {'signature': signature}
            if doc:
                func_info['doc'] = doc
                
            # Extract function calls
            func_body_lines = []
            brace_count = 0
            in_func_body = False
            for j in range(i+1, len(lines)):
                line_content = lines[j]
                if '{' in line_content:
                    brace_count += line_content.count('{')
                    in_func_body = True
                if in_func_body:
                    func_body_lines.append(line_content)
                if '}' in line_content:
                    brace_count -= line_content.count('}')
                    if brace_count <= 0:
                        break
            
            if func_body_lines:
                func_body = '\n'.join(func_body_lines)
                calls = extract_function_calls_shell(func_body, all_function_names)
                if calls:
                    func_info['calls'] = calls
            
            result['functions'][func_name] = func_info
            continue
            
        # Check for function definition (style 2)
        match = re.match(func_pattern2, stripped)
        if match:
            func_name = match.group(1)
            result['functions'][func_name] = {'signature': '()'}
            continue
        
        # Check for exports
        match = re.match(export_pattern, stripped)
        if match:
            var_name = match.group(1)
            var_value = match.group(3) if match.group(3) else None
            if var_value:
                if var_value.startswith(("'", '"')):
                    var_type = 'str'
                elif var_value.isdigit():
                    var_type = 'number'
                else:
                    var_type = 'value'
                result['exports'][var_name] = var_type
            continue
        
        # Check for regular variables (uppercase)
        match = re.match(var_pattern, stripped)
        if match:
            var_name = match.group(1)
            if var_name not in result['exports'] and var_name not in result['variables']:
                result['variables'].append(var_name)
            continue
        
        # Check for source/dot includes
        for source_pattern in source_patterns:
            match = re.match(source_pattern, stripped)
            if match:
                if len(match.groups()) == 2:
                    sourced_file = match.group(2)
                else:
                    sourced_file = match.group(1)
                
                sourced_file = sourced_file.strip()
                if sourced_file and sourced_file not in result['sources']:
                    result['sources'].append(sourced_file)
                break
    
    # Clean up empty collections
    if not result['variables']:
        del result['variables']
    if not result['exports']:
        del result['exports']
    if not result['sources']:
        del result['sources']
    
    return result

def extract_markdown_structure(file_path: Path) -> Dict[str, List[str]]:
    """Extract headers and architectural hints from markdown files."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except:
        return {'sections': [], 'architecture_hints': []}
    
    # Extract headers (up to level 3)
    headers = re.findall(r'^#{1,3}\s+(.+)$', content[:5000], re.MULTILINE)
    
    # Look for architectural hints
    arch_patterns = [
        r'(?:located?|found?|stored?)\s+in\s+`?([\w\-\./]+)`?',
        r'`?([\w\-\./]+)`?\s+(?:contains?|houses?|holds?)',
        r'(?:see|check|look)\s+(?:in\s+)?`?([\w\-\./]+)`?\s+for',
        r'(?:file|module|component)\s+`?([\w\-\./]+)`?',
    ]
    
    hints = set()
    for pattern in arch_patterns:
        matches = re.findall(pattern, content[:5000], re.IGNORECASE)
        for match in matches:
            if '/' in match and not match.startswith('http'):
                hints.add(match)
    
    return {
        'sections': headers[:10],
        'architecture_hints': list(hints)[:5]
    }

# ============================================================================
# FUNCTION CALL EXTRACTION
# ============================================================================

def extract_function_calls_python(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from Python code body."""
    calls = set()
    
    call_pattern = r'\b(\w+)\s*\('
    exclude_keywords = {
        'if', 'elif', 'while', 'for', 'with', 'except', 'def', 'class',
        'return', 'yield', 'raise', 'assert', 'print', 'len', 'str', 
        'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple', 'type',
        'isinstance', 'issubclass', 'super', 'range', 'enumerate', 'zip',
        'map', 'filter', 'sorted', 'reversed', 'open', 'input', 'eval'
    }
    
    for match in re.finditer(call_pattern, body):
        func_name = match.group(1)
        if func_name in all_functions and func_name not in exclude_keywords:
            calls.add(func_name)
    
    # Also catch method calls like self.method() or obj.method()
    method_pattern = r'(?:self|cls|\w+)\.(\w+)\s*\('
    for match in re.finditer(method_pattern, body):
        method_name = match.group(1)
        if method_name in all_functions:
            calls.add(method_name)
    
    return sorted(list(calls))

def extract_function_calls_javascript(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from JavaScript/TypeScript code body."""
    calls = set()
    
    call_pattern = r'\b(\w+)\s*\('
    exclude_keywords = {
        'if', 'while', 'for', 'switch', 'catch', 'function', 'class',
        'return', 'throw', 'new', 'typeof', 'instanceof', 'void',
        'console', 'Array', 'Object', 'String', 'Number', 'Boolean',
        'Promise', 'Math', 'Date', 'JSON', 'parseInt', 'parseFloat'
    }
    
    for match in re.finditer(call_pattern, body):
        func_name = match.group(1)
        if func_name in all_functions and func_name not in exclude_keywords:
            calls.add(func_name)
    
    # Method calls: obj.method() or this.method()
    method_pattern = r'(?:this|\w+)\.(\w+)\s*\('
    for match in re.finditer(method_pattern, body):
        method_name = match.group(1)
        if method_name in all_functions:
            calls.add(method_name)
    
    return sorted(list(calls))

def extract_function_calls_shell(body: str, all_functions: Set[str]) -> List[str]:
    """Extract function calls from shell script body."""
    calls = set()
    
    for func_name in all_functions:
        patterns = [
            rf'^\s*{func_name}\b',  # Start of line
            rf'[;&|]\s*{func_name}\b',  # After operators
            rf'\$\({func_name}\b',  # Command substitution
            rf'`{func_name}\b',  # Backtick substitution
        ]
        for pattern in patterns:
            if re.search(pattern, body, re.MULTILINE):
                calls.add(func_name)
                break
    
    return sorted(list(calls))

def build_call_graph(functions: Dict, classes: Dict) -> Tuple[Dict, Dict]:
    """Build bidirectional call graph from extracted functions and methods."""
    calls_map = {}
    called_by_map = {}
    
    for func_name, func_info in functions.items():
        if isinstance(func_info, dict) and 'calls' in func_info:
            calls_map[func_name] = func_info['calls']
    
    for class_name, class_info in classes.items():
        if isinstance(class_info, dict) and 'methods' in class_info:
            for method_name, method_info in class_info['methods'].items():
                if isinstance(method_info, dict) and 'calls' in method_info:
                    full_method_name = f"{class_name}.{method_name}"
                    calls_map[full_method_name] = method_info['calls']
    
    for func_name, called_funcs in calls_map.items():
        for called_func in called_funcs:
            if called_func not in called_by_map:
                called_by_map[called_func] = []
            if func_name not in called_by_map[called_func]:
                called_by_map[called_func].append(func_name)
    
    return calls_map, called_by_map