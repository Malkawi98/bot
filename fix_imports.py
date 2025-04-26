#!/usr/bin/env python
"""
Script to find and fix absolute imports that use 'src.app' to use 'app' instead.
This helps resolve ModuleNotFoundError issues when running the app from within the src directory.
"""
import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if the file contains 'from src.app' or 'import src.app'
    if 'from src.app' in content or 'import src.app' in content:
        print(f"Fixing imports in {file_path}")
        
        # Replace 'from src.app' with 'from app'
        modified_content = re.sub(r'from src\.app', 'from app', content)
        
        # Replace 'import src.app' with 'import app'
        modified_content = re.sub(r'import src\.app', 'import app', modified_content)
        
        # Write the modified content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        return True
    
    return False

def find_and_fix_imports(directory):
    """Find and fix imports in all Python files in the directory."""
    fixed_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_imports_in_file(file_path):
                    fixed_files.append(file_path)
    
    return fixed_files

if __name__ == '__main__':
    src_dir = Path(__file__).parent / 'src'
    fixed_files = find_and_fix_imports(src_dir)
    
    if fixed_files:
        print(f"\nFixed imports in {len(fixed_files)} files:")
        for file in fixed_files:
            print(f"  - {file}")
    else:
        print("No files needed fixing.")
