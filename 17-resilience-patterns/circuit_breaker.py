"""
Circuit Breaker Pattern
=======================
Prevent cascading failures by failing fast when a service is unhealthy.
"""

import time
import threading
import asyncio
import functools
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, Type, Tuple
from collections import deque
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Circuit Breaker States
# =============================================================================

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


# =============================================================================
# Circuit Breaker Configuration
# =============================================================================

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 3           # Successes in half-open to close
    timeout: float = 30.0                # Seconds before trying half-open
    half_open_max_calls: int = 3         # Max concurrent calls in half-open
    exclude_exceptions: Tuple[Type[Exception], ...] = ()  # Don't count these
    
    # Sliding window configuration
    window_size: int = 10                # Number of calls to track
    failure_rate_threshold: float = 0.5  # 50% failure rate opens circuit


# =============================================================================
# Circuit Breaker Implementation
# =============================================================================

class CircuitBreaker:
    """
    Circuit Breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Requests fail immediately without calling the service
    - HALF_OPEN: Allow limited requests to test if service recovered
    
    Transitions:
    - CLOSED -> OPEN: When failure threshold is exceeded
    - OPEN -> HALF_OPEN: After timeout period
    - HALF_OPEN -> CLOSED: When success threshold is met
    - HALF_OPEN -> OPEN: On any failure
    """
    
    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        # Sliding window for failure rate calculation
        self._call_results: deque = deque(maxlen=self.config.window_size)
        
        self._lock = threading.Lock()
        self._state_change_callbacks: list = []
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_state_transition()
            return self._state
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if not self._call_results:
            return 0.0
        failures = sum(1 for r in self._call_results if not r)
        return failures / len(self._call_results)
    
    def _check_state_transition(self) -> None:
        """Check and perform state transitions."""
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.config.timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._call_results.clear()
        
        logger.info(f"Circuit '{self.name}': {old_state.value} -> {new_state.value}")
        
        # Notify callbacks
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception:
                pass
    
    def on_state_change(self, callback: Callable) -> None:
        """Register callback for state changes."""
        self._state_change_callbacks.append(callback)
    
    def _record_success(self) -> None:
        """Record a successful call."""
        self._call_results.append(True)
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
    
    def _record_failure(self) -> None:
        """Record a failed call."""
        self._call_results.append(False)
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        
        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open reopens the circuit
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            # Check failure threshold
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)
            # Or check failure rate
            elif (len(self._call_results) >= self.config.window_size and
                  self.failure_rate >= self.config.failure_rate_threshold):
                self._transition_to(CircuitState.OPEN)
    
    def can_execute(self) -> bool:
        """Check if a call can be made."""
        with self._lock:
            self._check_state_transition()
            
            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                return False
            else:  # HALF_OPEN
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
    
    def record_result(self, success: bool, exception: Optional[Exception] = None) -> None:
        """Record the result of a call."""
        with self._lock:
            # Check if exception should be excluded
            if exception and isinstance(exception, self.config.exclude_exceptions):
                return
            
            if success:
                self._record_success()
            else:
                self._record_failure()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker."""
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is OPEN"
            )
        
        try:
            result = func(*args, **kwargs)
            self.record_result(success=True)
            return result
        except Exception as e:
            self.record_result(success=False, exception=e)
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute an async function through the circuit breaker."""
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is OPEN"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_result(success=True)
            return result
        except Exception as e:
            self.record_result(success=False, exception=e)
            raise
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_rate": self.failure_rate,
                "window_size": len(self._call_results),
            }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# =============================================================================
# Circuit Breaker Decorator
# =============================================================================

def circuit_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 30.0,
    exclude_exceptions: Tuple[Type[Exception], ...] = (),
):
    """
    Decorator to protect a function with a circuit breaker.
    
    Usage:
        @circuit_breaker(name="external_api", failure_threshold=3)
        def call_external_api():
            ...
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout,
        exclude_exceptions=exclude_exceptions,
    )
    
    cb = CircuitBreaker(name=name, config=config)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        # Attach circuit breaker for inspection
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator


def async_circuit_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout: float = 30.0,
    exclude_exceptions: Tuple[Type[Exception], ...] = (),
):
    """Async version of circuit breaker decorator."""
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout,
        exclude_exceptions=exclude_exceptions,
    )
    
    cb = CircuitBreaker(name=name, config=config)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call_async(func, *args, **kwargs)
        
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator


# =============================================================================
# Circuit Breaker Registry
# =============================================================================

class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._breakers = {}
            return cls._instance
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_stats(self) -> dict:
        """Get stats for all circuit breakers."""
        return {
            name: cb.get_stats()
            for name, cb in self._breakers.items()
        }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._breakers.values():
            cb.reset()


# Global registry
registry = CircuitBreakerRegistry()


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Circuit Breaker Pattern Demo")
    print("=" * 60)
    
    # Create circuit breaker
    cb = CircuitBreaker(
        name="demo",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=5.0,
        )
    )
    
    # Add state change listener
    cb.on_state_change(lambda old, new: print(f"  State changed: {old.value} -> {new.value}"))
    
    # Simulate failing service
    call_count = 0
    
    def unreliable_service():
        global call_count
        call_count += 1
        
        if call_count <= 5:  # First 5 calls fail
            raise ConnectionError(f"Connection failed (call {call_count})")
        return f"Success (call {call_count})"
    
    print("\n=== Simulating Failures ===\n")
    
    for i in range(10):
        try:
            result = cb.call(unreliable_service)
            print(f"Call {i+1}: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Call {i+1}: BLOCKED - {e}")
        except ConnectionError as e:
            print(f"Call {i+1}: FAILED - {e}")
        
        print(f"  Stats: {cb.get_stats()}")
        time.sleep(0.1)
    
    # Wait for timeout
    print(f"\n=== Waiting for timeout ({cb.config.timeout}s) ===\n")
    time.sleep(cb.config.timeout + 0.5)
    
    print("=== After Timeout (Half-Open) ===\n")
    
    for i in range(5):
        try:
            result = cb.call(unreliable_service)
            print(f"Call {i+1}: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Call {i+1}: BLOCKED - {e}")
        except ConnectionError as e:
            print(f"Call {i+1}: FAILED - {e}")
        
        print(f"  Stats: {cb.get_stats()}")
    
    # Decorator example
    print("\n=== Using Decorator ===\n")
    
    @circuit_breaker(name="decorated", failure_threshold=2, timeout=2.0)
    def decorated_service():
        raise ValueError("Always fails")
    
    for i in range(5):
        try:
            decorated_service()
        except CircuitBreakerOpenError:
            print(f"Call {i+1}: Circuit is OPEN")
        except ValueError:
            print(f"Call {i+1}: Service failed")
    
    print(f"\nDecorated service stats: {decorated_service.circuit_breaker.get_stats()}")
    
    print("\n" + "=" * 60)
