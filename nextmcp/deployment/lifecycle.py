"""
Application lifecycle management for NextMCP.

Provides graceful shutdown handling for production deployments:
- SIGTERM/SIGINT signal handling
- Waiting for in-flight requests
- Resource cleanup
"""

import asyncio
import logging
import signal
import sys
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Graceful shutdown handler for NextMCP applications.

    Handles SIGTERM and SIGINT signals to allow graceful shutdown:
    - Stops accepting new requests
    - Waits for in-flight requests to complete
    - Runs cleanup handlers
    - Exits with appropriate status code

    Example:
        >>> shutdown = GracefulShutdown(timeout=30)
        >>> shutdown.add_cleanup_handler(close_database)
        >>> shutdown.register()
        >>> # Application will shutdown gracefully on SIGTERM/SIGINT
    """

    def __init__(self, timeout: float = 30.0):
        """
        Initialize graceful shutdown handler.

        Args:
            timeout: Maximum time (in seconds) to wait for shutdown
        """
        self.timeout = timeout
        self._cleanup_handlers: list[Callable[[], Any]] = []
        self._shutdown_event: asyncio.Event | None = None
        self._is_shutting_down = False
        self._original_handlers: dict[signal.Signals, Any] = {}

    def add_cleanup_handler(self, handler: Callable[[], Any]) -> None:
        """
        Add a cleanup handler to run during shutdown.

        Handlers are run in the order they were added.

        Args:
            handler: Callable to run during shutdown (can be sync or async)
        """
        self._cleanup_handlers.append(handler)

    def register(self) -> None:
        """
        Register signal handlers for graceful shutdown.

        Registers handlers for SIGTERM and SIGINT.
        """
        # Store original handlers
        self._original_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, self._handle_signal)
        self._original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self._handle_signal)
        logger.info("Registered graceful shutdown handlers for SIGTERM and SIGINT")

    def unregister(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
        logger.info("Unregistered graceful shutdown handlers")

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signal."""
        sig = signal.Signals(signum)
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")

        if self._is_shutting_down:
            logger.warning("Shutdown already in progress, ignoring signal")
            return

        self._is_shutting_down = True

        # If we have an event loop, schedule async shutdown
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._shutdown_async())
            else:
                # Synchronous shutdown
                self._shutdown_sync()
        except RuntimeError:
            # No event loop, use sync shutdown
            self._shutdown_sync()

    async def _shutdown_async(self) -> None:
        """Perform async graceful shutdown."""
        logger.info(f"Starting async graceful shutdown (timeout: {self.timeout}s)...")

        try:
            # Wait for shutdown event with timeout
            if self._shutdown_event:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Shutdown timeout ({self.timeout}s) exceeded, forcing shutdown")

        # Run cleanup handlers
        await self._run_cleanup_handlers()

        logger.info("Graceful shutdown complete, exiting")
        sys.exit(0)

    def _shutdown_sync(self) -> None:
        """Perform synchronous graceful shutdown."""
        logger.info(f"Starting synchronous graceful shutdown (timeout: {self.timeout}s)...")

        # Run cleanup handlers synchronously
        for handler in self._cleanup_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    logger.warning(f"Cannot run async handler {handler.__name__} in sync shutdown")
                else:
                    logger.info(f"Running cleanup handler: {handler.__name__}")
                    handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler.__name__}: {e}", exc_info=True)

        logger.info("Graceful shutdown complete, exiting")
        sys.exit(0)

    async def _run_cleanup_handlers(self) -> None:
        """Run all cleanup handlers (async and sync)."""
        for handler in self._cleanup_handlers:
            try:
                logger.info(f"Running cleanup handler: {handler.__name__}")
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler.__name__}: {e}", exc_info=True)

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._is_shutting_down

    def set_shutdown_event(self, event: asyncio.Event) -> None:
        """
        Set the event to wait for during shutdown.

        This allows the application to signal when it's safe to shutdown
        (e.g., when all in-flight requests have completed).

        Args:
            event: Event to wait for during shutdown
        """
        self._shutdown_event = event
