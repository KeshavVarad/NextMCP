"""
Integration tests for NextMCP.from_config() with auto-discovery.
"""

import tempfile
from pathlib import Path

import pytest

from nextmcp import NextMCP


class TestFromConfigIntegration:
    """Test the from_config() class method with real project structures."""

    def test_from_config_with_blog_example(self):
        """Test loading the blog example project."""
        blog_path = Path(__file__).parent.parent / "examples" / "blog_server"

        if not blog_path.exists():
            pytest.skip("Blog example not found")

        # Load the app from config
        app = NextMCP.from_config(base_path=str(blog_path))

        # Verify app was created
        assert app.name == "blog-server"
        assert "blog" in app.description.lower()

        # Verify tools were discovered
        tools = app.get_tools()
        assert len(tools) >= 5
        assert "create_post" in tools
        assert "get_post" in tools
        assert "list_posts" in tools
        assert "update_post" in tools
        assert "delete_post" in tools

        # Verify prompts were discovered
        prompts = app.get_prompts()
        assert len(prompts) >= 3
        assert "write_post_prompt" in prompts
        assert "edit_post_prompt" in prompts
        assert "content_strategy_prompt" in prompts

        # Verify resources were discovered
        resources = app.get_resources()
        assert len(resources) >= 3  # Direct resources
        assert "blog://stats" in resources
        assert "blog://config" in resources
        assert "blog://authors" in resources

    def test_from_config_without_config_file(self):
        """Test from_config() with no config file (should use defaults)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create minimal structure
            tools_dir = base_path / "tools"
            tools_dir.mkdir()

            # Create a simple tool (don't use "test_" prefix - those are skipped!)
            (tools_dir / "my_tool.py").write_text(
                """
from nextmcp import tool

@tool()
def test_function() -> str:
    return "test"
"""
            )

            # Load without config file (should work with defaults)
            app = NextMCP.from_config(base_path=str(base_path))

            # Verify it used defaults
            assert app.name == "mcp-server"
            assert len(app.get_tools()) == 1
            assert "test_function" in app.get_tools()

    def test_from_config_with_custom_paths(self):
        """Test from_config() with custom discovery paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create config with custom paths
            config_content = """
name: custom-server
auto_discover: true
discovery:
  tools: my_tools/
  prompts: my_prompts/
  resources: my_resources/
"""
            (base_path / "nextmcp.config.yaml").write_text(config_content)

            # Create custom directories
            (base_path / "my_tools").mkdir()
            (base_path / "my_prompts").mkdir()
            (base_path / "my_resources").mkdir()

            # Add tools in custom directory
            (base_path / "my_tools" / "custom.py").write_text(
                """
from nextmcp import tool

@tool()
def custom_tool() -> str:
    return "custom"
"""
            )

            # Load with custom config
            app = NextMCP.from_config(base_path=str(base_path))

            assert app.name == "custom-server"
            assert "custom_tool" in app.get_tools()

    def test_from_config_with_auto_discover_disabled(self):
        """Test that auto_discover: false prevents discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create config with auto_discover disabled
            config_content = """
name: manual-server
auto_discover: false
"""
            (base_path / "nextmcp.config.yaml").write_text(config_content)

            # Create tools directory
            tools_dir = base_path / "tools"
            tools_dir.mkdir()
            (tools_dir / "tool.py").write_text(
                """
from nextmcp import tool

@tool()
def should_not_be_discovered() -> str:
    return "test"
"""
            )

            # Load with auto_discover disabled
            app = NextMCP.from_config(base_path=str(base_path))

            # No tools should be discovered
            assert len(app.get_tools()) == 0

    def test_from_config_discovers_all_primitive_types(self):
        """Test that from_config discovers tools, prompts, and resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create standard structure
            (base_path / "tools").mkdir()
            (base_path / "prompts").mkdir()
            (base_path / "resources").mkdir()

            # Create tool
            (base_path / "tools" / "t.py").write_text(
                """
from nextmcp import tool

@tool()
def my_tool() -> str:
    return "tool"
"""
            )

            # Create prompt
            (base_path / "prompts" / "p.py").write_text(
                """
from nextmcp import prompt

@prompt()
def my_prompt(param: str) -> str:
    return f"prompt: {param}"
"""
            )

            # Create resource
            (base_path / "resources" / "r.py").write_text(
                """
from nextmcp import resource

@resource("test://resource")
def my_resource() -> dict:
    return {"data": "resource"}
"""
            )

            app = NextMCP.from_config(base_path=str(base_path))

            assert len(app.get_tools()) == 1
            assert len(app.get_prompts()) == 1
            assert len(app.get_resources()) == 1

    def test_from_config_with_nested_modules(self):
        """Test that nested modules are discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Create nested structure
            nested_dir = base_path / "tools" / "database" / "queries"
            nested_dir.mkdir(parents=True)

            (nested_dir / "select.py").write_text(
                """
from nextmcp import tool

@tool()
def select_query(table: str) -> str:
    return f"SELECT * FROM {table}"
"""
            )

            app = NextMCP.from_config(base_path=str(base_path))

            assert "select_query" in app.get_tools()


def test_blog_example_can_be_imported():
    """Test that the blog example can be imported without errors."""
    blog_path = Path(__file__).parent.parent / "examples" / "blog_server"

    if not blog_path.exists():
        pytest.skip("Blog example not found")

    import sys

    sys.path.insert(0, str(blog_path))

    try:
        # These imports should not raise errors
        from prompts import workflows
        from resources import blog_resources
        from tools import posts

        # Verify functions exist
        assert hasattr(posts, "create_post")
        assert hasattr(workflows, "write_post_prompt")
        assert hasattr(blog_resources, "blog_stats")

    finally:
        sys.path.remove(str(blog_path))
