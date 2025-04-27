#!/usr/bin/env python3
"""
Script to fix Alembic migration issues by creating a merge migration
and updating the alembic_version table to reflect the current state.
"""
import os
import sys
import subprocess
from pathlib import Path

# Get the absolute path to the project directory
PROJECT_DIR = Path(__file__).parent.absolute()
SRC_DIR = PROJECT_DIR / "src"

def run_command(cmd, cwd=None):
    """Run a shell command and return its output"""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd, 
        shell=True, 
        cwd=cwd or PROJECT_DIR,
        capture_output=True, 
        text=True
    )
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
        return False, result.stderr
    return True, result.stdout

def create_merge_migration():
    """Create a merge migration to combine multiple heads"""
    cmd = "cd src && alembic merge heads -m 'merge_multiple_heads'"
    success, output = run_command(cmd)
    if not success:
        print("Failed to create merge migration")
        return False
    print("Successfully created merge migration")
    return True

def update_alembic_version_table():
    """Update the alembic_version table to reflect the current state"""
    # Get the latest revision ID from the merge migration
    cmd = "cd src && alembic heads"
    success, output = run_command(cmd)
    if not success:
        print("Failed to get latest revision")
        return False
    
    # Extract the revision ID from the output
    revision_id = None
    for line in output.splitlines():
        if line.strip().startswith("Rev:"):
            revision_id = line.split("Rev:")[1].strip().split(" ")[0]
            break
    
    if not revision_id:
        print("Could not find revision ID in output")
        return False
    
    # Create a Python script to update the alembic_version table
    update_script = f"""
import sqlite3

# Connect to the database
conn = sqlite3.connect('src/app.db')
cursor = conn.cursor()

# Check if alembic_version table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
if not cursor.fetchone():
    # Create alembic_version table if it doesn't exist
    cursor.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    print("Created alembic_version table")
else:
    # Clear existing entries
    cursor.execute("DELETE FROM alembic_version")
    print("Cleared existing entries in alembic_version table")

# Insert the latest revision ID
cursor.execute("INSERT INTO alembic_version (version_num) VALUES (?)", ('{revision_id}',))
print(f"Inserted revision ID: {revision_id}")

# Commit changes and close connection
conn.commit()
conn.close()
print("Database updated successfully")
"""
    
    # Write the update script to a temporary file
    with open("update_alembic.py", "w") as f:
        f.write(update_script)
    
    # Run the update script
    cmd = "python update_alembic.py"
    success, output = run_command(cmd)
    if not success:
        print("Failed to update alembic_version table")
        return False
    
    print(output)
    
    # Remove the temporary script
    os.remove("update_alembic.py")
    return True

def main():
    """Main function to fix migration issues"""
    print("Starting migration fix process...")
    
    # Step 1: Create a merge migration
    if not create_merge_migration():
        sys.exit(1)
    
    # Step 2: Update the alembic_version table
    if not update_alembic_version_table():
        sys.exit(1)
    
    print("\nMigration fix process completed successfully!")
    print("\nYou can now run your application with:")
    print("docker-compose -f docker-compose.prod.yml up -d")

if __name__ == "__main__":
    main()
