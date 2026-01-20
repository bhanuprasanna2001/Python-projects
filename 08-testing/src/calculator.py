"""Calculator module to demonstrate testing."""

from typing import Union

Number = Union[int, float]


class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a: Number, b: Number) -> Number:
        """Add two numbers."""
        result = a + b
        self._record(f"{a} + {b} = {result}")
        return result
    
    def subtract(self, a: Number, b: Number) -> Number:
        """Subtract b from a."""
        result = a - b
        self._record(f"{a} - {b} = {result}")
        return result
    
    def multiply(self, a: Number, b: Number) -> Number:
        """Multiply two numbers."""
        result = a * b
        self._record(f"{a} * {b} = {result}")
        return result
    
    def divide(self, a: Number, b: Number) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self._record(f"{a} / {b} = {result}")
        return result
    
    def power(self, base: Number, exponent: Number) -> Number:
        """Raise base to the power of exponent."""
        result = base ** exponent
        self._record(f"{base} ^ {exponent} = {result}")
        return result
    
    def _record(self, operation: str):
        """Record operation in history."""
        self.history.append(operation)
    
    def get_history(self) -> list:
        """Get calculation history."""
        return self.history.copy()
    
    def clear_history(self):
        """Clear calculation history."""
        self.history.clear()


# Standalone functions
def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number."""
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n < 0:
        raise ValueError("Fibonacci not defined for negative numbers")
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
