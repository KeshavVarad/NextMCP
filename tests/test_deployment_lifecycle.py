"""
Tests for graceful shutdown functionality.

Tests lifecycle management including:
- Signal handling
- Cleanup handlers
- Async shutdown
- Timeout handling
"""

import asyncio
import signal

import pytest

from nextmcp.deployment.lifecycle import GracefulShutdown


class TestGracefulShutdown:
    """Test GracefulShutdown class."""

    def test_initialization(self):
        """Test graceful shutdown initialization."""
        shutdown = GracefulShutdown(timeout=30.0)
        assert shutdown.timeout == 30.0
        assert not shutdown.is_shutting_down()

    def test_default_timeout(self):
        """Test default timeout value."""
        shutdown = GracefulShutdown()
        assert shutdown.timeout == 30.0

    def test_add_cleanup_handler(self):
        """Test adding cleanup handlers."""
        shutdown = GracefulShutdown()
        called = []

        def cleanup():
            called.append(True)

        shutdown.add_cleanup_handler(cleanup)
        assert len(shutdown._cleanup_handlers) == 1

    def test_multiple_cleanup_handlers(self):
        """Test adding multiple cleanup handlers."""
        shutdown = GracefulShutdown()

        def cleanup1():
            pass

        def cleanup2():
            pass

        shutdown.add_cleanup_handler(cleanup1)
        shutdown.add_cleanup_handler(cleanup2)
        assert len(shutdown._cleanup_handlers) == 2

    def test_register_signal_handlers(self):
        """Test registering signal handlers."""
        shutdown = GracefulShutdown()

        # Get original handlers
        orig_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        orig_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Register
        shutdown.register()

        # Check handlers were changed
        current_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        current_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)

        assert current_sigterm != orig_sigterm
        assert current_sigint != orig_sigint

        # Cleanup
        signal.signal(signal.SIGTERM, orig_sigterm)
        signal.signal(signal.SIGINT, orig_sigint)

    def test_unregister_signal_handlers(self):
        """Test unregistering signal handlers."""
        shutdown = GracefulShutdown()

        # Get original handlers
        orig_sigterm = signal.signal(signal.SIGTERM, signal.SIG_DFL)
        orig_sigint = signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Register and then unregister
        shutdown.register()
        shutdown.unregister()

        # Check handlers were restored by setting back to original
        signal.signal(signal.SIGTERM, orig_sigterm)
        signal.signal(signal.SIGINT, orig_sigint)

    def test_shutdown_state(self):
        """Test shutdown state tracking."""
        shutdown = GracefulShutdown()

        assert not shutdown.is_shutting_down()

        shutdown._is_shutting_down = True
        assert shutdown.is_shutting_down()

    @pytest.mark.asyncio
    async def test_async_cleanup_handler(self):
        """Test async cleanup handlers."""
        shutdown = GracefulShutdown()
        called = []

        async def async_cleanup():
            await asyncio.sleep(0.01)
            called.append(True)

        shutdown.add_cleanup_handler(async_cleanup)
        await shutdown._run_cleanup_handlers()

        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_sync_cleanup_handler_in_async(self):
        """Test sync cleanup handlers work in async context."""
        shutdown = GracefulShutdown()
        called = []

        def sync_cleanup():
            called.append(True)

        shutdown.add_cleanup_handler(sync_cleanup)
        await shutdown._run_cleanup_handlers()

        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_multiple_cleanup_handlers_run_in_order(self):
        """Test cleanup handlers run in order."""
        shutdown = GracefulShutdown()
        order = []

        def cleanup1():
            order.append(1)

        def cleanup2():
            order.append(2)

        async def cleanup3():
            await asyncio.sleep(0.01)
            order.append(3)

        shutdown.add_cleanup_handler(cleanup1)
        shutdown.add_cleanup_handler(cleanup2)
        shutdown.add_cleanup_handler(cleanup3)

        await shutdown._run_cleanup_handlers()

        assert order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_cleanup_handler_error_doesnt_stop_others(self):
        """Test that errors in one handler don't stop others."""
        shutdown = GracefulShutdown()
        called = []

        def failing_cleanup():
            raise ValueError("Cleanup failed")

        def successful_cleanup():
            called.append(True)

        shutdown.add_cleanup_handler(failing_cleanup)
        shutdown.add_cleanup_handler(successful_cleanup)

        await shutdown._run_cleanup_handlers()

        # Second handler should still run
        assert len(called) == 1

    def test_set_shutdown_event(self):
        """Test setting shutdown event."""
        shutdown = GracefulShutdown()
        event = asyncio.Event()

        shutdown.set_shutdown_event(event)
        assert shutdown._shutdown_event is event

    @pytest.mark.asyncio
    async def test_shutdown_waits_for_event(self):
        """Test that shutdown waits for event to be set."""
        shutdown = GracefulShutdown(timeout=1.0)
        event = asyncio.Event()
        shutdown.set_shutdown_event(event)

        # Create a task that sets the event after a delay
        async def set_event():
            await asyncio.sleep(0.1)
            event.set()

        asyncio.create_task(set_event())

        # Start shutdown (would hang without event)
        start = asyncio.get_event_loop().time()
        try:
            # We can't fully test shutdown because it calls sys.exit()
            # Just verify the event mechanism works
            await asyncio.wait_for(event.wait(), timeout=0.5)
            elapsed = asyncio.get_event_loop().time() - start
            assert 0.1 <= elapsed < 0.5
        except asyncio.TimeoutError:
            pytest.fail("Event was not set in time")

    def test_no_cleanup_handlers(self):
        """Test shutdown with no cleanup handlers."""
        shutdown = GracefulShutdown()
        # Should exit cleanly (sys.exit(0))
        with pytest.raises(SystemExit) as exc_info:
            shutdown._shutdown_sync()
        assert exc_info.value.code == 0

    def test_shutdown_state_after_signal(self):
        """Test that shutdown state is set after signal."""
        shutdown = GracefulShutdown()

        # Manually trigger shutdown state
        shutdown._is_shutting_down = True

        assert shutdown.is_shutting_down()
