#!/usr/bin/env python3
import fnmatch
import os
import shutil
import subprocess  # nosec

CLEAN_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "leads_*.csv",
    "leads_*.xlsx",
    "test_*.py",
    "*_test.py",
    "get-pip.py",
]

EXCLUDE_DIRS = {".git", ".venv", "venv", "env", "node_modules"}


def clean_files(root_dir="."):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        # Remove matching files
        for pattern in CLEAN_PATTERNS:
            for filename in fnmatch.filter(filenames, pattern):
                file_path = os.path.join(dirpath, filename)
                print(f"Removing {file_path}")
                os.remove(file_path)
        # Remove matching directories
        for dirname in list(dirnames):
            if fnmatch.fnmatch(dirname, "__pycache__"):
                dir_path = os.path.join(dirpath, dirname)
                print(f"Removing directory {dir_path}")
                shutil.rmtree(dir_path)


def run_formatters():
    print("Running black...")
    subprocess.run(["black", "."])  # nosec
    print("Running isort...")
    subprocess.run(["isort", "."])  # nosec


def main():
    clean_files()
    if input("Run code formatters (black, isort)? [y/N]: ").lower() == "y":
        run_formatters()


if __name__ == "__main__":
    main()
