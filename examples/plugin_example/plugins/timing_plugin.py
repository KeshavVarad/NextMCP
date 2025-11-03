"""
Timing Plugin - Example plugin that adds timing middleware.

This demonstrates:
- Creating middleware in a plugin
- Using plugin lifecycle hooks
- Tracking state in plugins
"""

from nextmcp import Plugin
import time


class TimingPlugin(Plugin):
    """Plugin that adds timing middleware to measure tool execution time."""

    name = "timing-plugin"
    version = "1.0.0"
    description = "Adds timing middleware to track tool execution time"
    author = "NextMCP Examples"

    def __init__(self):
        super().__init__()
        self.timing_enabled = True

    def on_init(self):
        """Initialize plugin state."""
        print(f"Initializing {self.name}...")

    def on_load(self, app):
        """Add timing middleware to the application."""

        def timing_middleware(fn):
            """Middleware that times function execution."""
            def wrapper(*args, **kwargs):
                if not self.timing_enabled:
                    return fn(*args, **kwargs)

                start_time = time.time()
                result = fn(*args, **kwargs)
                end_time = time.time()
                elapsed = (end_time - start_time) * 1000  # Convert to ms

                tool_name = getattr(fn, '_tool_name', fn.__name__)
                print(f"⏱️  Tool '{tool_name}' took {elapsed:.2f}ms")

                return result
            return wrapper

        app.add_middleware(timing_middleware)
        print(f"✓ {self.name} loaded: Added timing middleware")

    def on_unload(self):
        """Cleanup when plugin is unloaded."""
        print(f"Unloading {self.name}...")
        self.timing_enabled = False
