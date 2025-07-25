#!/usr/bin/env python3
"""
Final script to fix specific linting errors in app.py
"""

def fix_specific_errors():
    """Fix the specific linting errors mentioned in the GitHub build failure."""
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
    print("✅ Fixed all linting errors in app.py")


if __name__ == "__main__":
    fix_specific_errors() 