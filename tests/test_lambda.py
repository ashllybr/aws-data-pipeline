import pytest
import sys
import os
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
    assert os.path.exists('../requirements.txt'), "requirements.txt not found"

def test_lambda_function_exists():
    """Test that lambda_function.py exists"""
    assert os.path.exists('../lambda_function.py'), "lambda_function.py not found"

def test_readme_exists():
    """Test that README.md exists"""
    assert os.path.exists('../README.md'), "README.md not found"

if __name__ == '__main__':
    pytest.main()