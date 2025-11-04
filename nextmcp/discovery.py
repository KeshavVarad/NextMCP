"""
Auto-discovery engine for NextMCP.

This module provides automatic discovery and registration of tools, prompts,
and resources from directory structures, enabling convention-based project organization.
"""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AutoDiscovery:
    """
    Automatically discover and register tools, prompts, and resources from directories.

    This is the core differentiation feature that enables convention-based structure,
    similar to Next.js's file-based routing.
    """

    def __init__(self, base_path: str | Path | None = None):
        """
        Initialize the auto-discovery engine.

        Args:
            base_path: Base directory for discovery (defaults to current directory)
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.discovered_tools: list[tuple[str, Any]] = []
        self.discovered_prompts: list[tuple[str, Any]] = []
        self.discovered_resources: list[tuple[str, Any]] = []
        self.discovered_resource_templates: list[tuple[str, Any]] = []

    def discover_all(
        self,
        tools_dir: str = "tools",
        prompts_dir: str = "prompts",
        resources_dir: str = "resources",
    ) -> dict[str, list]:
        """
        Discover all primitives from standard directory structure.

        Args:
            tools_dir: Directory containing tools
            prompts_dir: Directory containing prompts
            resources_dir: Directory containing resources

        Returns:
            Dictionary with discovered tools, prompts, and resources
        """
        results = {
            "tools": self.discover_tools(tools_dir),
            "prompts": self.discover_prompts(prompts_dir),
            "resources": self.discover_resources(resources_dir),
        }

        logger.info(
            f"Auto-discovery complete: "
            f"{len(results['tools'])} tools, "
            f"{len(results['prompts'])} prompts, "
            f"{len(results['resources'])} resources"
        )

        return results

    def discover_tools(self, directory: str = "tools") -> list[tuple[str, Any]]:
        """
        Scan directory for @tool decorated functions.

        Args:
            directory: Directory to scan for tools

        Returns:
            List of (name, function) tuples for discovered tools
        """
        tools_path = self.base_path / directory
        if not tools_path.exists():
            logger.debug(f"Tools directory not found: {tools_path}")
            return []

        tools = []
        for module_path in self._find_python_modules(tools_path):
            module_tools = self._discover_in_module(module_path, "_tool_name")
            tools.extend(module_tools)

        logger.info(f"Discovered {len(tools)} tools in {directory}/")
        return tools

    def discover_prompts(self, directory: str = "prompts") -> list[tuple[str, Any]]:
        """
        Scan directory for @prompt decorated functions.

        Args:
            directory: Directory to scan for prompts

        Returns:
            List of (name, function) tuples for discovered prompts
        """
        prompts_path = self.base_path / directory
        if not prompts_path.exists():
            logger.debug(f"Prompts directory not found: {prompts_path}")
            return []

        prompts = []
        for module_path in self._find_python_modules(prompts_path):
            module_prompts = self._discover_in_module(module_path, "_prompt_name")
            prompts.extend(module_prompts)

        logger.info(f"Discovered {len(prompts)} prompts in {directory}/")
        return prompts

    def discover_resources(self, directory: str = "resources") -> list[tuple[str, Any]]:
        """
        Scan directory for @resource and @resource_template decorated functions.

        Args:
            directory: Directory to scan for resources

        Returns:
            List of (name, function) tuples for discovered resources
        """
        resources_path = self.base_path / directory
        if not resources_path.exists():
            logger.debug(f"Resources directory not found: {resources_path}")
            return []

        resources = []
        for module_path in self._find_python_modules(resources_path):
            # Discover direct resources
            module_resources = self._discover_in_module(module_path, "_resource_uri")
            resources.extend(module_resources)

            # Discover resource templates (they have _resource_template attribute)
            module_templates = self._discover_resource_templates(module_path)
            resources.extend(module_templates)

        logger.info(f"Discovered {len(resources)} resources in {directory}/")
        return resources

    def _find_python_modules(self, directory: Path) -> list[Path]:
        """
        Find all Python modules in a directory (recursively).

        Args:
            directory: Directory to search

        Returns:
            List of Python file paths
        """
        if not directory.exists():
            return []

        modules = []
        for path in directory.rglob("*.py"):
            # Skip __init__.py files and test files
            if path.name == "__init__.py" or path.name.startswith("test_"):
                continue
            modules.append(path)

        return sorted(modules)

    def _discover_in_module(
        self, module_path: Path, marker_attribute: str
    ) -> list[tuple[str, Any]]:
        """
        Discover decorated functions in a Python module.

        Args:
            module_path: Path to the Python module
            marker_attribute: Attribute name that marks decorated functions
                             (e.g., "_tool_name", "_prompt_name", "_resource_uri")

        Returns:
            List of (name, function) tuples
        """
        try:
            # Import the module dynamically
            module = self._import_module_from_path(module_path)
            if not module:
                return []

            discovered = []
            for _name, obj in inspect.getmembers(module):
                # Check if object has the marker attribute (indicating decoration)
                if hasattr(obj, marker_attribute) and callable(obj):
                    # Get the name from the marker attribute
                    decorated_name = getattr(obj, marker_attribute)
                    discovered.append((decorated_name, obj))
                    logger.debug(
                        f"Discovered {marker_attribute[1:-5]}: {decorated_name} "
                        f"from {module_path.name}"
                    )

            return discovered

        except Exception as e:
            logger.error(f"Error discovering from {module_path}: {e}")
            return []

    def _discover_resource_templates(self, module_path: Path) -> list[tuple[str, Any]]:
        """
        Discover resource templates in a Python module.

        Args:
            module_path: Path to the Python module

        Returns:
            List of (uri_pattern, function) tuples for templates
        """
        try:
            module = self._import_module_from_path(module_path)
            if not module:
                return []

            discovered = []
            for _name, obj in inspect.getmembers(module):
                # Check if object has _resource_template attribute
                if hasattr(obj, "_resource_template") and callable(obj):
                    template = obj._resource_template
                    # Use uri_pattern as the identifier
                    uri_pattern = template.uri_pattern
                    discovered.append((uri_pattern, obj))
                    logger.debug(
                        f"Discovered resource template: {uri_pattern} " f"from {module_path.name}"
                    )

            return discovered

        except Exception as e:
            logger.error(f"Error discovering templates from {module_path}: {e}")
            return []

    def _import_module_from_path(self, module_path: Path) -> Any | None:
        """
        Dynamically import a Python module from a file path.

        Args:
            module_path: Path to the Python file

        Returns:
            Imported module or None if import fails
        """
        try:
            # Generate module name from path (use unique name to avoid conflicts)
            module_name = f"_nextmcp_discovery_{module_path.stem}_{id(module_path)}"

            # Add parent directory to sys.path temporarily
            parent_dir = str(module_path.parent)
            path_added = False
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
                path_added = True

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    return module

                return None
            finally:
                # Clean up sys.path
                if path_added and parent_dir in sys.path:
                    sys.path.remove(parent_dir)

        except Exception as e:
            logger.error(f"Failed to import module {module_path}: {e}", exc_info=True)
            return None


class FileWatcher:
    """
    Watch directories for file changes and trigger reloads.

    This enables hot reload functionality during development.
    """

    def __init__(self, directories: list[str | Path], callback: Any):
        """
        Initialize the file watcher.

        Args:
            directories: Directories to watch
            callback: Function to call when changes detected
        """
        self.directories = [Path(d) for d in directories]
        self.callback = callback
        self._watching = False

    def start(self) -> None:
        """Start watching directories for changes."""
        try:
            import watchdog.events  # noqa: F401

            logger.info(f"Starting file watcher for {len(self.directories)} directories")
            self._watching = True

            # Implementation would use watchdog to monitor file changes
            # This is a placeholder for the full implementation

        except ImportError:
            logger.warning(
                "watchdog package not installed. Hot reload disabled. "
                "Install with: pip install watchdog"
            )

    def stop(self) -> None:
        """Stop watching directories."""
        self._watching = False
        logger.info("File watcher stopped")


def validate_project_structure(base_path: str | Path | None = None) -> dict[str, Any]:
    """
    Validate that a project follows NextMCP conventions.

    Args:
        base_path: Base directory of the project

    Returns:
        Dictionary with validation results
    """
    base_path = Path(base_path) if base_path else Path.cwd()

    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "stats": {},
    }

    # Check for expected directories
    expected_dirs = ["tools", "prompts", "resources"]
    found_dirs = []

    for dir_name in expected_dirs:
        dir_path = base_path / dir_name
        if dir_path.exists():
            found_dirs.append(dir_name)
            # Count Python files
            py_files = list(dir_path.rglob("*.py"))
            py_files = [f for f in py_files if f.name != "__init__.py"]
            results["stats"][dir_name] = len(py_files)
        else:
            results["warnings"].append(f"Directory '{dir_name}/' not found")

    if not found_dirs:
        results["errors"].append("No standard directories (tools/, prompts/, resources/) found")
        results["valid"] = False

    # Check for config file
    config_file = base_path / "nextmcp.config.yaml"
    if not config_file.exists():
        results["warnings"].append("No nextmcp.config.yaml found (optional but recommended)")

    # Check for __init__.py files
    for dir_name in found_dirs:
        init_file = base_path / dir_name / "__init__.py"
        if not init_file.exists():
            results["warnings"].append(f"No __init__.py in {dir_name}/ (recommended)")

    return results
