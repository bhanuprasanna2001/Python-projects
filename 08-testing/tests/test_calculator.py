"""
Test Calculator Module
======================
Demonstrates pytest testing patterns.
"""

import pytest
from src.calculator import Calculator, factorial, fibonacci


# ============================================================
# Basic Tests
# ============================================================

class TestCalculatorBasic:
    """Basic calculator tests."""
    
    def test_add(self):
        """Test addition."""
        calc = Calculator()
        assert calc.add(2, 3) == 5
    
    def test_subtract(self):
        """Test subtraction."""
        calc = Calculator()
        assert calc.subtract(5, 3) == 2
    
    def test_multiply(self):
        """Test multiplication."""
        calc = Calculator()
        assert calc.multiply(4, 3) == 12
    
    def test_divide(self):
        """Test division."""
        calc = Calculator()
        assert calc.divide(10, 2) == 5.0
    
    def test_divide_by_zero(self):
        """Test division by zero raises error."""
        calc = Calculator()
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            calc.divide(10, 0)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def calculator():
    """Provide a fresh Calculator instance."""
    return Calculator()


@pytest.fixture
def calculator_with_history():
    """Provide Calculator with some history."""
    calc = Calculator()
    calc.add(1, 1)
    calc.subtract(5, 3)
    return calc


class TestWithFixtures:
    """Tests using fixtures."""
    
    def test_add_with_fixture(self, calculator):
        """Use calculator fixture."""
        assert calculator.add(10, 20) == 30
    
    def test_history_starts_empty(self, calculator):
        """History should start empty."""
        assert calculator.get_history() == []
    
    def test_history_records_operations(self, calculator):
        """Operations should be recorded."""
        calculator.add(1, 2)
        calculator.multiply(3, 4)
        
        history = calculator.get_history()
        assert len(history) == 2
        assert "1 + 2 = 3" in history[0]
    
    def test_clear_history(self, calculator_with_history):
        """Test clearing history."""
        assert len(calculator_with_history.get_history()) > 0
        
        calculator_with_history.clear_history()
        
        assert calculator_with_history.get_history() == []


# ============================================================
# Parametrized Tests
# ============================================================

@pytest.mark.parametrize("a, b, expected", [
    (1, 1, 2),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
    (1.5, 2.5, 4.0),
])
def test_add_parametrized(calculator, a, b, expected):
    """Test addition with multiple inputs."""
    assert calculator.add(a, b) == expected


@pytest.mark.parametrize("a, b, expected", [
    (10, 2, 5.0),
    (9, 3, 3.0),
    (7, 2, 3.5),
    (1, 4, 0.25),
])
def test_divide_parametrized(calculator, a, b, expected):
    """Test division with multiple inputs."""
    assert calculator.divide(a, b) == expected


@pytest.mark.parametrize("base, exp, expected", [
    (2, 3, 8),
    (10, 2, 100),
    (5, 0, 1),
    (2, -1, 0.5),
])
def test_power_parametrized(calculator, base, exp, expected):
    """Test power with multiple inputs."""
    assert calculator.power(base, exp) == expected


# ============================================================
# Testing Standalone Functions
# ============================================================

class TestFactorial:
    """Test factorial function."""
    
    @pytest.mark.parametrize("n, expected", [
        (0, 1),
        (1, 1),
        (5, 120),
        (10, 3628800),
    ])
    def test_factorial_valid(self, n, expected):
        """Test factorial with valid inputs."""
        assert factorial(n) == expected
    
    def test_factorial_negative(self):
        """Factorial should raise for negative numbers."""
        with pytest.raises(ValueError):
            factorial(-1)
    
    def test_factorial_non_integer(self):
        """Factorial should raise for non-integers."""
        with pytest.raises(TypeError):
            factorial(3.5)


class TestFibonacci:
    """Test Fibonacci function."""
    
    @pytest.mark.parametrize("n, expected", [
        (0, 0),
        (1, 1),
        (2, 1),
        (10, 55),
        (20, 6765),
    ])
    def test_fibonacci_valid(self, n, expected):
        """Test Fibonacci with valid inputs."""
        assert fibonacci(n) == expected
    
    def test_fibonacci_negative(self):
        """Fibonacci should raise for negative numbers."""
        with pytest.raises(ValueError):
            fibonacci(-1)


# ============================================================
# Test Markers
# ============================================================

@pytest.mark.slow
def test_large_calculation(calculator):
    """A slow test (marked for selective running)."""
    result = 0
    for i in range(1000):
        result = calculator.add(result, i)
    assert result == sum(range(1000))


@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    """This test is skipped."""
    pass


@pytest.mark.skipif(True, reason="Conditional skip")
def test_conditional_skip():
    """This test is conditionally skipped."""
    pass


# ============================================================
# Testing Exceptions
# ============================================================

class TestExceptions:
    """Test exception handling."""
    
    def test_divide_by_zero_message(self, calculator):
        """Check exception message."""
        with pytest.raises(ValueError) as exc_info:
            calculator.divide(10, 0)
        
        assert "Cannot divide by zero" in str(exc_info.value)
    
    def test_factorial_type_error(self):
        """Check TypeError for wrong type."""
        with pytest.raises(TypeError) as exc_info:
            factorial("5")
        
        assert "integer" in str(exc_info.value).lower()
