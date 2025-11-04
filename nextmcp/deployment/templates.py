"""
Template rendering system for NextMCP deployment files.

Provides utilities for rendering deployment configuration templates:
- Dockerfile
- docker-compose.yml
- Platform-specific configs
"""

import re
from pathlib import Path
from typing import Any


class TemplateRenderer:
    """
    Simple template renderer using Jinja2-like syntax.

    Supports:
    - Variable substitution: {{ var_name }}
    - Default values: {{ var_name | default("value") }}
    - Conditionals: {% if condition %} ... {% endif %}
    """

    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates"

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of template file (e.g., "docker/Dockerfile.template")
            context: Dictionary of variables to substitute

        Returns:
            Rendered template string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path) as f:
            template_content = f.read()

        return self._render_string(template_content, context)

    def _render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render a template string with the given context."""
        result = template

        # Handle conditionals first: {% if var %} ... {% endif %}
        result = self._process_conditionals(result, context)

        # Handle variable substitution with defaults: {{ var | default("value") }}
        result = self._process_variables(result, context)

        return result

    def _process_conditionals(self, template: str, context: dict[str, Any]) -> str:
        """Process {% if %} conditionals."""
        # Pattern: {% if var_name %} content {% endif %}
        pattern = r"{%\s*if\s+(\w+)\s*%}(.*?){%\s*endif\s*%}"

        def replace_conditional(match: re.Match) -> str:
            var_name = match.group(1)
            content = match.group(2)
            # Check if variable exists and is truthy
            if context.get(var_name):
                return content
            return ""

        return re.sub(pattern, replace_conditional, template, flags=re.DOTALL)

    def _process_variables(self, template: str, context: dict[str, Any]) -> str:
        """Process {{ variable }} substitutions."""
        # Pattern: {{ var_name | default("value") }} or {{ var_name }}
        pattern = r"{{\s*(\w+)(?:\s*\|\s*default\([\"']([^\"']*)[\"']\))?\s*}}"

        def replace_variable(match: re.Match) -> str:
            var_name = match.group(1)
            default_value = match.group(2)

            # Get value from context
            value = context.get(var_name)

            # Use default if value is None
            if value is None:
                return default_value if default_value is not None else ""

            return str(value)

        return re.sub(pattern, replace_variable, template)

    def render_to_file(
        self, template_name: str, output_path: str | Path, context: dict[str, Any]
    ) -> None:
        """
        Render a template and write to file.

        Args:
            template_name: Name of template file
            output_path: Path to write rendered output
            context: Dictionary of variables to substitute
        """
        rendered = self.render(template_name, context)
        output_path = Path(output_path)

        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(rendered)

    def get_template_variables(self, template_name: str) -> set[str]:
        """
        Extract variable names from a template.

        Args:
            template_name: Name of template file

        Returns:
            Set of variable names found in template
        """
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path) as f:
            template_content = f.read()

        # Extract variable names from {{ var_name }} patterns
        var_pattern = r"{{\s*(\w+)"
        variables = set(re.findall(var_pattern, template_content))

        # Extract variable names from {% if var_name %} patterns
        if_pattern = r"{%\s*if\s+(\w+)\s*%}"
        variables.update(re.findall(if_pattern, template_content))

        return variables


def detect_app_config() -> dict[str, Any]:
    """
    Auto-detect application configuration from current directory.

    Returns:
        Dictionary with detected configuration values
    """
    config: dict[str, Any] = {
        "app_name": Path.cwd().name,
        "port": 8000,
        "app_file": "app.py",
        "with_database": False,
        "with_redis": False,
    }

    # Check for common app files
    for app_file in ["app.py", "server.py", "main.py"]:
        if Path(app_file).exists():
            config["app_file"] = app_file
            break

    # Check for requirements.txt to detect dependencies
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        requirements = requirements_file.read_text()
        if "psycopg2" in requirements or "asyncpg" in requirements:
            config["with_database"] = True
        if "redis" in requirements:
            config["with_redis"] = True

    # Check for .env file for port configuration
    env_file = Path(".env")
    if env_file.exists():
        env_content = env_file.read_text()
        port_match = re.search(r"PORT=(\d+)", env_content)
        if port_match:
            config["port"] = int(port_match.group(1))

    return config
