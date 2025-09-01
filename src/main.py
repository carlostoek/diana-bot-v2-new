"""
Main application file
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import config, ENVIRONMENT

def main():
    """Main application entry point"""
    print(f"🚀 Application starting in {ENVIRONMENT} mode")
    
    # Your application logic here
    print("Hello, World!")
    print(f"Project root: {project_root}")
    
    return 0

if __name__ == "__main__":
    exit(main())
