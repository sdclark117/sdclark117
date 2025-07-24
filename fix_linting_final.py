#!/usr/bin/env python3
"""
Final script to fix specific linting errors in app.py
"""
import re

def fix_specific_errors():
    """Fix the specific linting errors mentioned in the GitHub build failure."""
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Remove trailing whitespace from all lines
    lines = content.split('\n')
    for i, line in enumerate(lines):
        lines[i] = line.rstrip()
    
    # Fix 2: Fix the specific indentation issue around line 1633
    for i, line in enumerate(lines):
        if 'return render_template("admin_dashboard.html",' in line:
            # Fix the continuation lines
            lines[i] = '        return render_template("admin_dashboard.html",'
            if i + 1 < len(lines) and 'users=users,' in lines[i + 1]:
                lines[i + 1] = '                             users=users,'
            if i + 2 < len(lines) and 'analytics_data=analytics_data,' in lines[i + 2]:
                lines[i + 2] = '                             analytics_data=analytics_data,'
            if i + 3 < len(lines) and 'total_users=total_users,' in lines[i + 3]:
                lines[i + 3] = '                             total_users=total_users,'
            if i + 4 < len(lines) and 'active_users_today=active_users_today,' in lines[i + 4]:
                lines[i + 4] = '                             active_users_today=active_users_today,'
            if i + 5 < len(lines) and 'plan_distribution=plan_distribution)' in lines[i + 5]:
                lines[i + 5] = '                             plan_distribution=plan_distribution)'
    
    # Write the fixed content back
    content = '\n'.join(lines)
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed all linting errors in app.py")

if __name__ == "__main__":
    fix_specific_errors() 