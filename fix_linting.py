#!/usr/bin/env python3
"""
Script to fix flake8 linting errors in app.py
"""

import re


def fix_app_py():
    """Fix linting errors in app.py"""
    # Read the file
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    # Remove trailing whitespace from all lines
    lines = [line.rstrip() for line in content.split('\n')]
    # Remove blank lines with whitespace
    lines = [line if line.strip() != '' or line == '' else '' for line in lines]
    # Write the fixed content back
    content = '\n'.join(lines) + '\n'
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Fixed linting errors in app.py")


if __name__ == "__main__":
    fix_app_py() 