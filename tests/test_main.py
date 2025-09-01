"""
Tests for main application
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import main

def test_main_function():
    """Test that main function runs without error"""
    result = main()
    assert result == 0

def test_project_structure():
    """Test that project structure exists"""
    assert project_root.exists()
    assert (project_root / "src").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "config").exists()

class TestProjectSetup:
    """Test class for project setup validation"""
    
    def test_config_file_exists(self):
        """Test that configuration file exists"""
        config_file = project_root / "config" / "config.py"
        assert config_file.exists()
    
    def test_main_file_exists(self):
        """Test that main application file exists"""
        main_file = project_root / "src" / "main.py"
        assert main_file.exists()
    
    def test_readme_exists(self):
        """Test that README file exists"""
        readme_file = project_root / "README.md"
        assert readme_file.exists()
