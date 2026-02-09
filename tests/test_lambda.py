import pytest
import sys
import os

# Add parent directory to path
sys.path.append('..')

def test_import_lambda():
    """Test that we can import the lambda function"""
    try:
        from lambda_function import lambda_handler
        assert True
    except ImportError as e:
        assert False, f"Cannot import lambda_function: {e}"

def test_requirements_exist():
    """Test that requirements.txt exists"""
    # Look in current directory (tests/) or parent directory
    if os.path.exists("requirements.txt"):
        assert True
    elif os.path.exists("../requirements.txt"):
        assert True
    else:
        assert False, "requirements.txt not found"

def test_lambda_function_exists():
    """Test that lambda_function.py exists"""
    if os.path.exists("lambda_function.py"):
        assert True
    elif os.path.exists("../lambda_function.py"):
        assert True
    else:
        assert False, "lambda_function.py not found"

def test_readme_exists():
    """Test that README.md exists"""
    if os.path.exists("README.md"):
        assert True
    elif os.path.exists("../README.md"):
        assert True
    else:
        assert False, "README.md not found"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])