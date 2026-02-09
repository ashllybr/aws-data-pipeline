import pytest

def test_always_passes():
    """Basic test that always passes"""
    assert True

def test_basic_math():
    """Test basic math operation"""
    assert 1 + 1 == 2

def test_list_length():
    """Test list operations"""
    my_list = [1, 2, 3]
    assert len(my_list) == 3

def test_string_operation():
    """Test string operations"""
    text = "hello"
    assert text.upper() == "HELLO"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])