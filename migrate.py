#!/usr/bin/env python
"""
Migration helper script for the FastAPI boilerplate project.
This script provides a simple way to run database migrations.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def run_migrations(action="upgrade", revision="head"):
    """Run Alembic migrations with the specified action and revision."""
    # Get the src directory
    src_dir = Path(__file__).resolve().parent / "src"
    
    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent)
    
    # Build the command
    cmd = ["alembic", action]
    if action in ["upgrade", "downgrade"]:
        cmd.append(revision)
    
    # Run the command
    try:
        result = subprocess.run(
            cmd,
            cwd=str(src_dir),
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

def create_migration(message):
    """Create a new migration with the given message."""
    return run_migrations(action="revision", revision=f"--autogenerate -m \"{message}\"")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database migration helper")
    subparsers = parser.add_subparsers(dest="command", help="Migration command")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database schema")
    upgrade_parser.add_argument("revision", nargs="?", default="head", help="Revision to upgrade to (default: head)")
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database schema")
    downgrade_parser.add_argument("revision", help="Revision to downgrade to (e.g., -1, hash)")
    
    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "upgrade":
        success = run_migrations("upgrade", args.revision)
    elif args.command == "downgrade":
        success = run_migrations("downgrade", args.revision)
    elif args.command == "create":
        success = create_migration(args.message)
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)
