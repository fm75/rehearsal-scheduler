#!/usr/bin/env python3
"""Analyze impact of creating models/intervals.py"""

import ast
import os
from pathlib import Path

def find_python_files(directory):
    """Find all Python files."""
    return list(Path(directory).rglob("*.py"))

def analyze_file(filepath):
    """Analyze imports and usage in a file."""
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
        except:
            return None
    
    imports = []
    time_usage = []
    datetime_usage = []
    
    for node in ast.walk(tree):
        # Find imports
        if isinstance(node, ast.ImportFrom):
            if node.module in ['datetime', 'time']:
                imports.append((node.module, [a.name for a in node.names]))
        
        # Find time/date usage
        if isinstance(node, ast.Call):
            if hasattr(node.func, 'id'):
                if 'time' in node.func.id.lower():
                    time_usage.append(node.func.id)
                if 'date' in node.func.id.lower():
                    datetime_usage.append(node.func.id)
    
    return {
        'file': str(filepath),
        'imports': imports,
        'time_usage': set(time_usage),
        'datetime_usage': set(datetime_usage)
    }

# Analyze source and tests
print("=" * 80)
print("REFACTORING IMPACT ANALYSIS: models/intervals.py")
print("=" * 80)

for directory in ['src/rehearsal_scheduler', 'test']:
    print(f"\n{directory}/")
    print("-" * 80)
    
    files = find_python_files(directory)
    affected_files = []
    
    for filepath in files:
        result = analyze_file(filepath)
        if result and (result['imports'] or result['time_usage'] or result['datetime_usage']):
            affected_files.append(result)
    
    for result in affected_files:
        rel_path = result['file'].replace(f"{directory}/", "")
        print(f"\n📄 {rel_path}")
        if result['imports']:
            print(f"   Imports: {result['imports']}")
        if result['time_usage']:
            print(f"   Time usage: {result['time_usage']}")
        if result['datetime_usage']:
            print(f"   Date usage: {result['datetime_usage']}")
    
    print(f"\n   Total affected: {len(affected_files)} files")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)
print("""
1. Create models/intervals.py with new classes
2. DON'T modify existing code yet - just add new module
3. Write tests for intervals.py FIRST
4. Gradually migrate one function at a time
5. Run full test suite after each migration
6. Git commit after each successful migration step
""")
