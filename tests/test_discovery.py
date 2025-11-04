"""
Tests for the auto-discovery engine.
"""

import tempfile
from pathlib import Path

import pytest

from nextmcp.discovery import AutoDiscovery, validate_project_structure


class TestAutoDiscovery:
    """Test the AutoDiscovery class."""

    def test_init_with_base_path(self):
        """Test initialization with custom base path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery = AutoDiscovery(base_path=tmpdir)
            assert discovery.base_path == Path(tmpdir)

    def test_init_without_base_path(self):
        """Test initialization with default base path."""
        discovery = AutoDiscovery()
        assert discovery.base_path == Path.cwd()

    def test_discover_tools_empty_directory(self):
        """Test discovering tools from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery = AutoDiscovery(base_path=tmpdir)
            tools = discovery.discover_tools()
            assert tools == []

    def test_discover_tools_with_decorated_functions(self):
        """Test discovering tools from directory with decorated functions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            tools_dir = base_path / "tools"
            tools_dir.mkdir()

            # Create a tool module
            tool_file = tools_dir / "weather.py"
            tool_file.write_text(
                """
from nextmcp import tool

@tool()
def get_weather(city: str) -> dict:
    return {"temp": 72, "city": city}

@tool(name="forecast")
def get_forecast(city: str) -> list:
    return [{"day": 1, "temp": 70}]
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            tools = discovery.discover_tools()

            assert len(tools) == 2
            tool_names = [name for name, _ in tools]
            assert "get_weather" in tool_names
            assert "forecast" in tool_names

    def test_discover_prompts_with_decorated_functions(self):
        """Test discovering prompts from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            prompts_dir = base_path / "prompts"
            prompts_dir.mkdir()

            # Create a prompt module
            prompt_file = prompts_dir / "vacation.py"
            prompt_file.write_text(
                """
from nextmcp import prompt

@prompt()
def vacation_planner(destination: str) -> str:
    return f"Plan trip to {destination}"

@prompt(name="budget_trip")
def budget_planner(dest: str, budget: int) -> str:
    return f"Budget trip to {dest}"
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            prompts = discovery.discover_prompts()

            assert len(prompts) == 2
            prompt_names = [name for name, _ in prompts]
            assert "vacation_planner" in prompt_names
            assert "budget_trip" in prompt_names

    def test_discover_resources_with_decorated_functions(self):
        """Test discovering resources from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            resources_dir = base_path / "resources"
            resources_dir.mkdir()

            # Create a resource module
            resource_file = resources_dir / "files.py"
            resource_file.write_text(
                """
from nextmcp import resource, resource_template

@resource("file:///logs/app.log")
def app_logs() -> str:
    return "log contents"

@resource_template("file:///docs/{category}/{filename}")
def documentation(category: str, filename: str) -> str:
    return f"doc: {category}/{filename}"
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            resources = discovery.discover_resources()

            assert len(resources) == 2
            # Check that both direct resources and templates are discovered
            resource_identifiers = [name for name, _ in resources]
            assert "file:///logs/app.log" in resource_identifiers
            assert "file:///docs/{category}/{filename}" in resource_identifiers

    def test_discover_all(self):
        """Test discovering all primitives at once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create directory structure
            (base_path / "tools").mkdir()
            (base_path / "prompts").mkdir()
            (base_path / "resources").mkdir()

            # Create files
            (base_path / "tools" / "weather.py").write_text(
                """
from nextmcp import tool

@tool()
def get_weather(city: str) -> dict:
    return {"temp": 72}
"""
            )

            (base_path / "prompts" / "vacation.py").write_text(
                """
from nextmcp import prompt

@prompt()
def plan_vacation(dest: str) -> str:
    return f"Plan {dest}"
"""
            )

            (base_path / "resources" / "files.py").write_text(
                """
from nextmcp import resource

@resource("file:///config.json")
def config() -> dict:
    return {"key": "value"}
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            results = discovery.discover_all()

            assert "tools" in results
            assert "prompts" in results
            assert "resources" in results
            assert len(results["tools"]) == 1
            assert len(results["prompts"]) == 1
            assert len(results["resources"]) == 1

    def test_discover_nested_modules(self):
        """Test discovering from nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            tools_dir = base_path / "tools"
            nested_dir = tools_dir / "database"
            nested_dir.mkdir(parents=True)

            # Create nested tool
            tool_file = nested_dir / "query.py"
            tool_file.write_text(
                """
from nextmcp import tool

@tool()
def execute_query(sql: str) -> list:
    return []
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            tools = discovery.discover_tools()

            assert len(tools) == 1
            assert tools[0][0] == "execute_query"

    def test_discover_skips_init_files(self):
        """Test that __init__.py files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            tools_dir = base_path / "tools"
            tools_dir.mkdir()

            # Create __init__.py (should be skipped)
            init_file = tools_dir / "__init__.py"
            init_file.write_text(
                """
from nextmcp import tool

@tool()
def should_be_skipped() -> str:
    return "skipped"
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            tools = discovery.discover_tools()

            # Should not discover tools from __init__.py
            assert len(tools) == 0

    def test_discover_skips_test_files(self):
        """Test that test files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            tools_dir = base_path / "tools"
            tools_dir.mkdir()

            # Create test file (should be skipped)
            test_file = tools_dir / "test_weather.py"
            test_file.write_text(
                """
from nextmcp import tool

@tool()
def test_tool() -> str:
    return "test"
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            tools = discovery.discover_tools()

            # Should not discover tools from test files
            assert len(tools) == 0

    def test_discover_handles_import_errors_gracefully(self):
        """Test that discovery handles import errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            tools_dir = base_path / "tools"
            tools_dir.mkdir()

            # Create file with syntax error
            bad_file = tools_dir / "bad.py"
            bad_file.write_text(
                """
from nextmcp import tool

@tool()
def broken_tool(
    # Missing closing parenthesis
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            # Should not raise exception
            tools = discovery.discover_tools()
            assert tools == []

    def test_discover_with_custom_directory_names(self):
        """Test discovering with custom directory names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            custom_dir = base_path / "my_tools"
            custom_dir.mkdir()

            tool_file = custom_dir / "weather.py"
            tool_file.write_text(
                """
from nextmcp import tool

@tool()
def get_weather(city: str) -> dict:
    return {"temp": 72}
"""
            )

            discovery = AutoDiscovery(base_path=tmpdir)
            tools = discovery.discover_tools(directory="my_tools")

            assert len(tools) == 1
            assert tools[0][0] == "get_weather"


class TestValidateProjectStructure:
    """Test the validate_project_structure function."""

    def test_validate_empty_directory(self):
        """Test validation of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_project_structure(tmpdir)

            assert result["valid"] is False
            assert len(result["errors"]) > 0
            assert any("No standard directories" in err for err in result["errors"])

    def test_validate_with_standard_directories(self):
        """Test validation with standard directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create standard directories
            (base_path / "tools").mkdir()
            (base_path / "prompts").mkdir()
            (base_path / "resources").mkdir()

            # Create __init__.py files
            (base_path / "tools" / "__init__.py").touch()
            (base_path / "prompts" / "__init__.py").touch()
            (base_path / "resources" / "__init__.py").touch()

            # Add some Python files
            (base_path / "tools" / "weather.py").write_text("# tool code")
            (base_path / "prompts" / "vacation.py").write_text("# prompt code")
            (base_path / "resources" / "files.py").write_text("# resource code")

            result = validate_project_structure(tmpdir)

            assert result["valid"] is True
            assert result["stats"]["tools"] == 1
            assert result["stats"]["prompts"] == 1
            assert result["stats"]["resources"] == 1
            assert len(result["errors"]) == 0

    def test_validate_warns_about_missing_config(self):
        """Test that validation warns about missing config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "tools").mkdir()

            result = validate_project_structure(tmpdir)

            assert any("nextmcp.config.yaml" in warn for warn in result["warnings"])

    def test_validate_warns_about_missing_init_files(self):
        """Test that validation warns about missing __init__.py files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "tools").mkdir()
            # Don't create __init__.py

            result = validate_project_structure(tmpdir)

            assert any("__init__.py" in warn for warn in result["warnings"])

    def test_validate_counts_files_correctly(self):
        """Test that validation counts Python files correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            tools_dir = base_path / "tools"
            tools_dir.mkdir()

            # Create multiple Python files
            (tools_dir / "tool1.py").touch()
            (tools_dir / "tool2.py").touch()
            (tools_dir / "tool3.py").touch()
            (tools_dir / "__init__.py").touch()  # Should not be counted

            result = validate_project_structure(tmpdir)

            assert result["stats"]["tools"] == 3  # __init__.py not counted


@pytest.mark.asyncio
async def test_discover_async_functions():
    """Test that async functions are discovered correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        tools_dir = base_path / "tools"
        tools_dir.mkdir()

        tool_file = tools_dir / "async_tools.py"
        tool_file.write_text(
            """
from nextmcp import tool

@tool()
async def async_tool(param: str) -> str:
    return f"async: {param}"
"""
        )

        discovery = AutoDiscovery(base_path=tmpdir)
        tools = discovery.discover_tools()

        assert len(tools) == 1
        assert tools[0][0] == "async_tool"


def test_discovery_multiple_files_in_directory():
    """Test discovering from multiple files in the same directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        tools_dir = base_path / "tools"
        tools_dir.mkdir()

        # Create multiple tool files
        (tools_dir / "weather.py").write_text(
            """
from nextmcp import tool

@tool()
def get_weather(city: str) -> dict:
    return {"temp": 72}
"""
        )

        (tools_dir / "search.py").write_text(
            """
from nextmcp import tool

@tool()
def search_web(query: str) -> list:
    return []

@tool()
def search_images(query: str) -> list:
    return []
"""
        )

        discovery = AutoDiscovery(base_path=tmpdir)
        tools = discovery.discover_tools()

        assert len(tools) == 3
        tool_names = [name for name, _ in tools]
        assert "get_weather" in tool_names
        assert "search_web" in tool_names
        assert "search_images" in tool_names
