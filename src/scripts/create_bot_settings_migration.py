#!/usr/bin/env python3
"""
Script to create a migration for the bot settings table
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

def main():
    """Create a migration for the bot settings table"""
    # Get the directory of the alembic.ini file
    alembic_dir = Path(__file__).resolve().parent.parent
    
    # Change to the directory containing alembic.ini
    os.chdir(alembic_dir)
    
    # Run the alembic command to create a new migration
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", "Add bot settings table"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error creating migration: {result.stderr}")
        sys.exit(1)
    
    print(f"Migration created successfully: {result.stdout}")
    
    # Print instructions for applying the migration
    print("\nTo apply the migration, run:")
    print("cd src && alembic upgrade head")


if __name__ == "__main__":
    main()
