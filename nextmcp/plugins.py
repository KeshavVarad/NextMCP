"""
Plugin system for NextMCP.

Allows extending NextMCP functionality through plugins that can:
- Register new tools
- Add middleware
- Extend configuration
- Add custom functionality

Example:
    from nextmcp.plugins import Plugin, PluginManager

    class MyPlugin(Plugin):
        name = "my-plugin"
        version = "1.0.0"

        def on_load(self, app):
            @app.tool()
            def my_tool():
                return "Hello from plugin!"
"""

import importlib
import importlib.util
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PluginMetadata:
    """Metadata about a plugin."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        author: str = "",
        dependencies: list[str] | None = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies or []

    def __repr__(self) -> str:
        return f"PluginMetadata(name={self.name}, version={self.version})"


class Plugin(ABC):
    """
    Base class for NextMCP plugins.

    Plugins can extend NextMCP by:
    - Registering tools via app.tool()
    - Adding middleware via app.add_middleware()
    - Accessing configuration
    - Adding custom initialization logic

    Example:
        class WeatherPlugin(Plugin):
            name = "weather"
            version = "1.0.0"
            description = "Weather information tools"

            def on_load(self, app):
                @app.tool()
                def get_weather(city: str):
                    return {"city": city, "temp": 72}

            def on_unload(self):
                # Cleanup logic here
                pass
    """

    # Plugin metadata (override in subclass)
    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = []

    def __init__(self):
        """Initialize the plugin."""
        self._app = None
        self._loaded = False
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            dependencies=self.dependencies,
        )

    @abstractmethod
    def on_load(self, app: Any) -> None:
        """
        Called when the plugin is loaded.

        This is where you should register tools, add middleware, etc.

        Args:
            app: The NextMCP application instance
        """
        pass

    def on_unload(self) -> None:
        """
        Called when the plugin is unloaded.

        Override this to add cleanup logic.
        """
        # Default implementation: no cleanup needed
        return

    def on_init(self) -> None:
        """
        Called during plugin initialization, before on_load.

        Override this for early setup that doesn't require the app.
        """
        # Default implementation: no initialization needed
        return

    @property
    def is_loaded(self) -> bool:
        """Check if plugin is loaded."""
        return self._loaded

    def __repr__(self) -> str:
        return f"<Plugin: {self.name} v{self.version}>"


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.

    Example:
        manager = PluginManager(app)
        manager.discover_plugins("./plugins")
        manager.load_all()
    """

    def __init__(self, app: Any):
        """
        Initialize the plugin manager.

        Args:
            app: The NextMCP application instance
        """
        self.app = app
        self._plugins: dict[str, Plugin] = {}
        self._plugin_paths: list[Path] = []

        logger.info("Initialized PluginManager")

    def register_plugin(self, plugin: Plugin) -> None:
        """
        Register a plugin instance.

        Args:
            plugin: Plugin instance to register

        Raises:
            ValueError: If plugin with same name already registered
        """
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' is already registered")

        self._plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")

    def register_plugin_class(self, plugin_class: type[Plugin]) -> None:
        """
        Register a plugin class (will be instantiated).

        Args:
            plugin_class: Plugin class to register
        """
        plugin = plugin_class()
        self.register_plugin(plugin)

    def load_plugin(self, name: str) -> None:
        """
        Load a specific plugin by name.

        Args:
            name: Name of the plugin to load

        Raises:
            KeyError: If plugin not found
            RuntimeError: If plugin fails to load
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")

        plugin = self._plugins[name]

        if plugin.is_loaded:
            logger.warning(f"Plugin '{name}' is already loaded")
            return

        try:
            # Check dependencies
            for dep in plugin.dependencies:
                if dep not in self._plugins:
                    raise RuntimeError(
                        f"Plugin '{name}' depends on '{dep}' which is not registered"
                    )
                if not self._plugins[dep].is_loaded:
                    logger.info(f"Loading dependency '{dep}' for '{name}'")
                    self.load_plugin(dep)

            # Initialize and load
            logger.info(f"Loading plugin: {name}")
            plugin.on_init()
            plugin._app = self.app
            plugin.on_load(self.app)
            plugin._loaded = True

            logger.info(f"Successfully loaded plugin: {name}")

        except Exception as e:
            logger.error(f"Failed to load plugin '{name}': {e}")
            raise RuntimeError(f"Failed to load plugin '{name}': {e}") from e

    def unload_plugin(self, name: str) -> None:
        """
        Unload a specific plugin by name.

        Args:
            name: Name of the plugin to unload

        Raises:
            KeyError: If plugin not found
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")

        plugin = self._plugins[name]

        if not plugin.is_loaded:
            logger.warning(f"Plugin '{name}' is not loaded")
            return

        try:
            logger.info(f"Unloading plugin: {name}")
            plugin.on_unload()
            plugin._loaded = False
            plugin._app = None

            logger.info(f"Successfully unloaded plugin: {name}")

        except Exception as e:
            logger.error(f"Failed to unload plugin '{name}': {e}")
            raise RuntimeError(f"Failed to unload plugin '{name}': {e}") from e

    def load_all(self) -> None:
        """Load all registered plugins."""
        logger.info(f"Loading {len(self._plugins)} plugin(s)")

        for name in self._plugins:
            if not self._plugins[name].is_loaded:
                try:
                    self.load_plugin(name)
                except Exception as e:
                    logger.error(f"Failed to load plugin '{name}': {e}")

    def unload_all(self) -> None:
        """Unload all loaded plugins."""
        logger.info("Unloading all plugins")

        for name in self._plugins:
            if self._plugins[name].is_loaded:
                try:
                    self.unload_plugin(name)
                except Exception as e:
                    logger.error(f"Failed to unload plugin '{name}': {e}")

    def discover_plugins(self, directory: str) -> None:
        """
        Discover and register plugins from a directory.

        Looks for Python files containing Plugin subclasses.

        Args:
            directory: Directory path to search for plugins
        """
        plugin_dir = Path(directory)

        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {directory}")
            return

        if not plugin_dir.is_dir():
            logger.warning(f"Plugin path is not a directory: {directory}")
            return

        logger.info(f"Discovering plugins in: {directory}")
        self._plugin_paths.append(plugin_dir)

        # Find all Python files
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                self._load_plugin_from_file(plugin_file)
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")

    def _load_plugin_from_file(self, file_path: Path) -> None:
        """
        Load a plugin from a Python file.

        Args:
            file_path: Path to the plugin file
        """
        module_name = f"nextmcp_plugin_{file_path.stem}"

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Could not load spec from {file_path}")
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Plugin subclasses
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                try:
                    self.register_plugin_class(obj)
                    logger.info(f"Discovered plugin: {obj.name} from {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to register plugin {name}: {e}")

    def get_plugin(self, name: str) -> Plugin | None:
        """
        Get a plugin by name.

        Args:
            name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """
        List all registered plugins with their metadata.

        Returns:
            List of plugin information dictionaries
        """
        return [
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "author": plugin.author,
                "loaded": plugin.is_loaded,
                "dependencies": plugin.dependencies,
            }
            for plugin in self._plugins.values()
        ]

    def __len__(self) -> int:
        """Return number of registered plugins."""
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._plugins

    def __repr__(self) -> str:
        loaded = sum(1 for p in self._plugins.values() if p.is_loaded)
        return f"<PluginManager: {len(self)} plugins, {loaded} loaded>"
