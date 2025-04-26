"""
Template configuration module for the application.
Provides a centralized way to manage template paths and configuration.
"""
import os
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Define possible template directories
TEMPLATE_PATHS = [
    "/code/app/templates",  # Docker container path
    str(Path(__file__).resolve().parent.parent / "templates"),  # Relative to this file
    "app/templates",  # Relative to working directory
    "src/app/templates"  # Development path
]

# Find the first directory that exists
template_dir = None
for path in TEMPLATE_PATHS:
    if os.path.exists(path):
        template_dir = path
        print(f"Using template directory: {template_dir}")
        break

# If no directory exists, use a default
if template_dir is None:
    template_dir = "/code/app/templates"
    print(f"Warning: No template directory found, defaulting to {template_dir}")

# Create a single templates instance to be imported by other modules
templates = Jinja2Templates(directory=template_dir)
