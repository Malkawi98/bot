#!/usr/bin/env python
"""
Script to run database migrations using Alembic.
This script ensures that the correct database connection is used.
"""
import os
import sys
import subprocess
from pathlib import Path

# Get the current directory
current_dir = Path(__file__).parent.absolute()

def run_migrations():
    """Run Alembic migrations."""
    # Set the PYTHONPATH to include the src directory
    env = os.environ.copy()
    env["PYTHONPATH"] = str(current_dir.parent)
    
    # Run alembic command
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(current_dir),
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
