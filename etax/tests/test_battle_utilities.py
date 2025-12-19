"""
Battle Tests for eTax Utility Infrastructure
Run with: bench run-tests --app etax --module etax.tests.test_battle_utilities
"""

from frappe.tests.utils import FrappeTestCase


class TestResilienceModule(FrappeTestCase):
    """Test resilience utilities."""

    def test_circuit_breaker_import(self):
        """Circuit breaker should be importable."""
        from etax.utils.resilience import CircuitBreaker, CircuitState
        self.assertIsNotNone(CircuitBreaker)
        self.assertIsNotNone(CircuitState)
    
    def test_circuit_breaker_as_decorator(self):
        """Circuit breaker should work as decorator."""
        from etax.utils.resilience import CircuitBreaker
        
        cb = CircuitBreaker(name="test_decorator_etax")
        
        @cb
        def test_func():
            return "success"
        
        self.assertEqual(test_func(), "success")
    
    def test_circuit_breaker_state(self):
        """Circuit breaker should track state."""
        from etax.utils.resilience import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="test_state_etax", failure_threshold=3)
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    def test_circuit_breaker_opens_on_failures(self):
        """Circuit breaker should open after failures."""
        from etax.utils.resilience import CircuitBreaker, CircuitState, CircuitBreakerOpen
        
        cb = CircuitBreaker(name="test_open_etax", failure_threshold=2, recovery_timeout=1)
        
        @cb
        def failing_func():
            raise ValueError("test error")
        
        for _ in range(2):
            try:
                failing_func()
            except ValueError:
                # Expected - we're testing that circuit breaker tracks failures
                pass
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        with self.assertRaises(CircuitBreakerOpen):
            failing_func()
    
    def test_rate_limiter(self):
        """Rate limiter should be available."""
        from etax.utils.resilience import RateLimiter, RateLimitExceeded
        
        limiter = RateLimiter(name="test_limiter_etax", calls=10, period=60)
        
        @limiter
        def rate_limited_func():
            return "ok"
        
        self.assertEqual(rate_limited_func(), "ok")
        self.assertIsNotNone(RateLimitExceeded)
    
    def test_retry_decorator(self):
        """Retry decorator should retry on failure."""
        from etax.utils.resilience import retry_with_backoff
        
        attempts = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def flaky_func():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("fail")
            return "success"
        
        self.assertEqual(flaky_func(), "success")
        self.assertEqual(attempts, 2)


class TestValidatorsModule(FrappeTestCase):
    """Test validators."""

    def test_validators_import(self):
        """Validators should be importable."""
        from etax.utils.validators import Validator, ValidationResult
        self.assertIsNotNone(Validator)
        self.assertIsNotNone(ValidationResult)


class TestIdempotencyModule(FrappeTestCase):
    """Test idempotency utilities."""

    def test_idempotency_manager(self):
        """IdempotencyManager should be available."""
        from etax.utils.idempotency import IdempotencyManager
        self.assertIsNotNone(IdempotencyManager())


class TestMetricsModule(FrappeTestCase):
    """Test metrics collection."""

    def test_metrics_collector(self):
        """MetricsCollector should be available."""
        from etax.utils.metrics import MetricsCollector
        self.assertIsNotNone(MetricsCollector())


class TestHealthModule(FrappeTestCase):
    """Test health check endpoints."""

    def test_health_endpoint(self):
        """Health endpoint should return status."""
        from etax.api.health import health
        self.assertIn("status", health())
    
    def test_liveness(self):
        """Liveness probe should return alive."""
        from etax.api.health import liveness
        self.assertIn("alive", liveness())
    
    def test_readiness(self):
        """Readiness probe should return ready status."""
        from etax.api.health import readiness
        self.assertIn("ready", readiness())


class TestBackgroundModule(FrappeTestCase):
    """Test background job utilities."""

    def test_enqueue_function(self):
        """Should have enqueue function."""
        from etax.utils.background import enqueue_with_retry
        self.assertIsNotNone(enqueue_with_retry)


class TestLoggingModule(FrappeTestCase):
    """Test logging utilities."""

    def test_logger_available(self):
        """Logger should be available."""
        from etax.utils.logging import get_logger
        self.assertIsNotNone(get_logger())


class TestCertificateModule(FrappeTestCase):
    """Test certificate utilities."""

    def test_certificate_module(self):
        """Certificate module should be importable."""
        from etax.tasks import certificate
        self.assertIsNotNone(certificate)


class TestIntegration(FrappeTestCase):
    """Integration tests."""

    def test_circuit_breaker_integration(self):
        """Test circuit breaker with real function."""
        from etax.utils.resilience import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="integration_cb_etax", failure_threshold=5)
        
        @cb
        def success_func():
            return "ok"
        
        self.assertEqual(success_func(), "ok")
        self.assertEqual(cb.state, CircuitState.CLOSED)
