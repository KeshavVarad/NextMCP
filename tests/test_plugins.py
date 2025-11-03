"""
Tests for the NextMCP plugin system.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from nextmcp import NextMCP, Plugin, PluginManager


# Test Plugins for testing

class SimplePlugin(Plugin):
    """A simple test plugin."""
    name = "simple-plugin"
    version = "1.0.0"
    description = "A simple test plugin"
    author = "Test Author"

    def on_load(self, app):
        @app.tool()
        def plugin_tool():
            """A tool from the plugin"""
            return "plugin_result"


class MiddlewarePlugin(Plugin):
    """Plugin that adds middleware."""
    name = "middleware-plugin"
    version = "1.0.0"

    def on_load(self, app):
        def custom_middleware(fn):
            def wrapper(*args, **kwargs):
                result = fn(*args, **kwargs)
                return f"middleware:{result}"
            return wrapper

        app.add_middleware(custom_middleware)


class DependentPlugin(Plugin):
    """Plugin with dependencies."""
    name = "dependent-plugin"
    version = "1.0.0"
    dependencies = ["simple-plugin"]

    def on_load(self, app):
        @app.tool()
        def dependent_tool():
            return "dependent_result"


class LifecyclePlugin(Plugin):
    """Plugin that tracks lifecycle."""
    name = "lifecycle-plugin"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self.init_called = False
        self.load_called = False
        self.unload_called = False

    def on_init(self):
        self.init_called = True

    def on_load(self, app):
        self.load_called = True

    def on_unload(self):
        self.unload_called = True


# Tests

def test_plugin_metadata():
    """Test plugin metadata creation."""
    plugin = SimplePlugin()

    assert plugin.name == "simple-plugin"
    assert plugin.version == "1.0.0"
    assert plugin.description == "A simple test plugin"
    assert plugin.author == "Test Author"
    assert plugin.metadata.name == "simple-plugin"


def test_plugin_manager_initialization():
    """Test plugin manager initialization."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    assert manager.app == app
    assert len(manager) == 0


def test_register_plugin():
    """Test plugin registration."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    plugin = SimplePlugin()
    manager.register_plugin(plugin)

    assert len(manager) == 1
    assert "simple-plugin" in manager
    assert manager.get_plugin("simple-plugin") == plugin


def test_register_plugin_class():
    """Test registering a plugin class."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(SimplePlugin)

    assert len(manager) == 1
    assert "simple-plugin" in manager


def test_duplicate_plugin_registration():
    """Test that duplicate plugin registration raises error."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    plugin = SimplePlugin()
    manager.register_plugin(plugin)

    with pytest.raises(ValueError, match="already registered"):
        manager.register_plugin(plugin)


def test_load_plugin():
    """Test loading a plugin."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(SimplePlugin)
    assert not manager.get_plugin("simple-plugin").is_loaded

    manager.load_plugin("simple-plugin")
    assert manager.get_plugin("simple-plugin").is_loaded

    # Plugin should have registered a tool
    assert "plugin_tool" in app.get_tools()


def test_load_nonexistent_plugin():
    """Test loading a plugin that doesn't exist."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    with pytest.raises(KeyError, match="not found"):
        manager.load_plugin("nonexistent")


def test_unload_plugin():
    """Test unloading a plugin."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(LifecyclePlugin)
    manager.load_plugin("lifecycle-plugin")

    plugin = manager.get_plugin("lifecycle-plugin")
    assert plugin.is_loaded

    manager.unload_plugin("lifecycle-plugin")
    assert not plugin.is_loaded
    assert plugin.unload_called


def test_plugin_lifecycle():
    """Test plugin lifecycle hooks."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(LifecyclePlugin)
    plugin = manager.get_plugin("lifecycle-plugin")

    assert not plugin.init_called
    assert not plugin.load_called
    assert not plugin.unload_called

    manager.load_plugin("lifecycle-plugin")
    assert plugin.init_called
    assert plugin.load_called

    manager.unload_plugin("lifecycle-plugin")
    assert plugin.unload_called


def test_plugin_with_dependencies():
    """Test plugin dependency resolution."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    # Register both plugins
    manager.register_plugin_class(SimplePlugin)
    manager.register_plugin_class(DependentPlugin)

    # Load dependent plugin - should auto-load dependency
    manager.load_plugin("dependent-plugin")

    assert manager.get_plugin("simple-plugin").is_loaded
    assert manager.get_plugin("dependent-plugin").is_loaded


def test_plugin_missing_dependency():
    """Test plugin with missing dependency fails."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(DependentPlugin)

    with pytest.raises(RuntimeError, match="depends on"):
        manager.load_plugin("dependent-plugin")


def test_load_all_plugins():
    """Test loading all registered plugins."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(SimplePlugin)
    manager.register_plugin_class(MiddlewarePlugin)

    manager.load_all()

    assert manager.get_plugin("simple-plugin").is_loaded
    assert manager.get_plugin("middleware-plugin").is_loaded


def test_unload_all_plugins():
    """Test unloading all plugins."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(SimplePlugin)
    manager.register_plugin_class(MiddlewarePlugin)
    manager.load_all()

    manager.unload_all()

    assert not manager.get_plugin("simple-plugin").is_loaded
    assert not manager.get_plugin("middleware-plugin").is_loaded


def test_list_plugins():
    """Test listing plugins."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(SimplePlugin)
    manager.load_plugin("simple-plugin")

    plugins = manager.list_plugins()

    assert len(plugins) == 1
    assert plugins[0]["name"] == "simple-plugin"
    assert plugins[0]["version"] == "1.0.0"
    assert plugins[0]["loaded"] is True


def test_discover_plugins_from_directory():
    """Test discovering plugins from a directory."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    # Create a temporary directory with a plugin file
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_file = Path(tmpdir) / "test_plugin.py"
        plugin_file.write_text('''
from nextmcp import Plugin

class DiscoveredPlugin(Plugin):
    name = "discovered-plugin"
    version = "1.0.0"

    def on_load(self, app):
        @app.tool()
        def discovered_tool():
            return "discovered"
''')

        manager.discover_plugins(tmpdir)

        assert "discovered-plugin" in manager


def test_discover_nonexistent_directory():
    """Test discovering from nonexistent directory."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    # Should not raise, just log warning
    manager.discover_plugins("/nonexistent/path")


def test_nextmcp_plugins_property():
    """Test NextMCP plugins property."""
    app = NextMCP("test-app")

    # Lazy initialization
    assert app._plugin_manager is None

    manager = app.plugins
    assert manager is not None
    assert isinstance(manager, PluginManager)
    assert manager.app == app

    # Second access returns same instance
    assert app.plugins is manager


def test_nextmcp_use_plugin_with_class():
    """Test NextMCP use_plugin with class."""
    app = NextMCP("test-app")

    app.use_plugin(SimplePlugin)

    assert "simple-plugin" in app.plugins
    assert app.plugins.get_plugin("simple-plugin").is_loaded
    assert "plugin_tool" in app.get_tools()


def test_nextmcp_use_plugin_with_instance():
    """Test NextMCP use_plugin with instance."""
    app = NextMCP("test-app")

    plugin = SimplePlugin()
    app.use_plugin(plugin)

    assert "simple-plugin" in app.plugins
    assert app.plugins.get_plugin("simple-plugin").is_loaded


def test_nextmcp_use_plugin_invalid_type():
    """Test use_plugin with invalid type."""
    app = NextMCP("test-app")

    with pytest.raises(TypeError, match="must be a Plugin"):
        app.use_plugin("not-a-plugin")


def test_nextmcp_discover_plugins():
    """Test NextMCP discover_plugins convenience method."""
    app = NextMCP("test-app")

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_file = Path(tmpdir) / "test_plugin.py"
        plugin_file.write_text('''
from nextmcp import Plugin

class ConveniencePlugin(Plugin):
    name = "convenience-plugin"
    version = "1.0.0"

    def on_load(self, app):
        pass
''')

        app.discover_plugins(tmpdir)

        assert "convenience-plugin" in app.plugins


def test_nextmcp_load_plugins():
    """Test NextMCP load_plugins convenience method."""
    app = NextMCP("test-app")

    app.plugins.register_plugin_class(SimplePlugin)
    app.load_plugins()

    assert app.plugins.get_plugin("simple-plugin").is_loaded


def test_plugin_can_add_middleware():
    """Test that plugins can add middleware."""
    app = NextMCP("test-app")

    app.use_plugin(MiddlewarePlugin)

    # Add a tool after plugin is loaded
    @app.tool()
    def test_tool():
        return "original"

    # The middleware should wrap the result
    result = test_tool()
    assert result == "middleware:original"


def test_plugin_manager_repr():
    """Test PluginManager __repr__."""
    app = NextMCP("test-app")
    manager = PluginManager(app)

    manager.register_plugin_class(SimplePlugin)
    manager.register_plugin_class(MiddlewarePlugin)
    manager.load_plugin("simple-plugin")

    repr_str = repr(manager)
    assert "PluginManager" in repr_str
    assert "2 plugins" in repr_str
    assert "1 loaded" in repr_str


def test_plugin_repr():
    """Test Plugin __repr__."""
    plugin = SimplePlugin()
    repr_str = repr(plugin)

    assert "Plugin" in repr_str
    assert "simple-plugin" in repr_str
    assert "1.0.0" in repr_str
