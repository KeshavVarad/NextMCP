"""
Tests for template rendering system.

Tests template rendering including:
- Variable substitution
- Default values
- Conditionals
- File rendering
"""

import tempfile
from pathlib import Path

import pytest

from nextmcp.deployment.templates import TemplateRenderer, detect_app_config


class TestTemplateRenderer:
    """Test TemplateRenderer class."""

    def test_initialization(self):
        """Test template renderer initialization."""
        renderer = TemplateRenderer()
        assert renderer.templates_dir.exists()

    def test_render_simple_variable(self):
        """Test rendering simple variable substitution."""
        renderer = TemplateRenderer()
        template = "Hello {{ name }}!"
        result = renderer._render_string(template, {"name": "World"})
        assert result == "Hello World!"

    def test_render_multiple_variables(self):
        """Test rendering multiple variables."""
        renderer = TemplateRenderer()
        template = "{{ greeting }} {{ name }}!"
        result = renderer._render_string(template, {"greeting": "Hello", "name": "World"})
        assert result == "Hello World!"

    def test_render_variable_with_default(self):
        """Test rendering variable with default value."""
        renderer = TemplateRenderer()
        template = '{{ name | default("Guest") }}'
        result = renderer._render_string(template, {})
        assert result == "Guest"

    def test_render_variable_with_default_override(self):
        """Test that provided value overrides default."""
        renderer = TemplateRenderer()
        template = '{{ name | default("Guest") }}'
        result = renderer._render_string(template, {"name": "John"})
        assert result == "John"

    def test_render_missing_variable_no_default(self):
        """Test that missing variable without default becomes empty."""
        renderer = TemplateRenderer()
        template = "Hello {{ name }}!"
        result = renderer._render_string(template, {})
        assert result == "Hello !"

    def test_render_conditional_true(self):
        """Test rendering conditional when true."""
        renderer = TemplateRenderer()
        template = "{% if with_db %}DATABASE=true{% endif %}"
        result = renderer._render_string(template, {"with_db": True})
        assert result == "DATABASE=true"

    def test_render_conditional_false(self):
        """Test rendering conditional when false."""
        renderer = TemplateRenderer()
        template = "{% if with_db %}DATABASE=true{% endif %}"
        result = renderer._render_string(template, {"with_db": False})
        assert result == ""

    def test_render_conditional_missing_variable(self):
        """Test conditional with missing variable evaluates to false."""
        renderer = TemplateRenderer()
        template = "{% if with_db %}DATABASE=true{% endif %}"
        result = renderer._render_string(template, {})
        assert result == ""

    def test_render_multiline_conditional(self):
        """Test rendering multiline conditional."""
        renderer = TemplateRenderer()
        template = """
        {% if with_db %}
        DATABASE_URL=postgres://localhost
        DATABASE_ENABLED=true
        {% endif %}
        """
        result = renderer._render_string(template, {"with_db": True})
        assert "DATABASE_URL" in result
        assert "DATABASE_ENABLED" in result

    def test_render_multiple_conditionals(self):
        """Test multiple conditionals in template."""
        renderer = TemplateRenderer()
        template = """
        {% if with_db %}DB=true{% endif %}
        {% if with_cache %}CACHE=true{% endif %}
        """
        result = renderer._render_string(template, {"with_db": True, "with_cache": True})
        assert "DB=true" in result
        assert "CACHE=true" in result

    def test_render_conditional_with_variables(self):
        """Test conditional containing variables."""
        renderer = TemplateRenderer()
        template = "{% if with_db %}DB={{ db_name }}{% endif %}"
        result = renderer._render_string(template, {"with_db": True, "db_name": "mydb"})
        assert result == "DB=mydb"

    def test_render_number_variable(self):
        """Test rendering numeric variables."""
        renderer = TemplateRenderer()
        template = "Port: {{ port }}"
        result = renderer._render_string(template, {"port": 8000})
        assert result == "Port: 8000"

    def test_render_actual_dockerfile_template(self):
        """Test rendering actual Dockerfile template."""
        renderer = TemplateRenderer()
        context = {
            "port": 8000,
            "app_file": "app.py",
        }
        result = renderer.render("docker/Dockerfile.template", context)

        assert "FROM python:3.10-slim" in result
        assert "EXPOSE 8000" in result
        assert 'CMD ["python", "app.py"]' in result

    def test_render_dockerfile_with_custom_port(self):
        """Test Dockerfile with custom port."""
        renderer = TemplateRenderer()
        context = {"port": 9000, "app_file": "server.py"}
        result = renderer.render("docker/Dockerfile.template", context)

        assert "EXPOSE 9000" in result
        assert 'CMD ["python", "server.py"]' in result

    def test_render_docker_compose_template(self):
        """Test rendering docker-compose template."""
        renderer = TemplateRenderer()
        context = {
            "app_name": "test-app",
            "port": 8000,
            "with_database": False,
            "with_redis": False,
        }
        result = renderer.render("docker/docker-compose.yml.template", context)

        assert "test-app:" in result
        assert "8000:8000" in result
        assert "postgres:" not in result
        assert "redis:" not in result

    def test_render_docker_compose_with_database(self):
        """Test docker-compose with database."""
        renderer = TemplateRenderer()
        context = {
            "app_name": "test-app",
            "port": 8000,
            "with_database": True,
            "with_redis": False,
        }
        result = renderer.render("docker/docker-compose.yml.template", context)

        assert "postgres:" in result
        assert "POSTGRES_" in result
        assert "depends_on:" in result

    def test_render_docker_compose_with_redis(self):
        """Test docker-compose with Redis."""
        renderer = TemplateRenderer()
        context = {
            "app_name": "test-app",
            "port": 8000,
            "with_database": False,
            "with_redis": True,
        }
        result = renderer.render("docker/docker-compose.yml.template", context)

        assert "redis:" in result
        assert "redis:7-alpine" in result

    def test_render_docker_compose_with_both(self):
        """Test docker-compose with both database and Redis."""
        renderer = TemplateRenderer()
        context = {
            "app_name": "test-app",
            "port": 8000,
            "with_database": True,
            "with_redis": True,
        }
        result = renderer.render("docker/docker-compose.yml.template", context)

        assert "postgres:" in result
        assert "redis:" in result
        assert "volumes:" in result

    def test_render_to_file(self):
        """Test rendering template to file."""
        renderer = TemplateRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.txt"
            template = "Hello {{ name }}!"
            context = {"name": "World"}

            # Create a temporary template
            template_path = renderer.templates_dir / "test_template.txt"
            template_path.write_text(template)

            try:
                renderer.render_to_file("test_template.txt", output_path, context)

                assert output_path.exists()
                assert output_path.read_text() == "Hello World!"
            finally:
                # Cleanup
                if template_path.exists():
                    template_path.unlink()

    def test_render_to_file_creates_directories(self):
        """Test that render_to_file creates parent directories."""
        renderer = TemplateRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "output.txt"
            template = "Test content"
            context = {}

            # Create a temporary template
            template_path = renderer.templates_dir / "test_template2.txt"
            template_path.write_text(template)

            try:
                renderer.render_to_file("test_template2.txt", output_path, context)

                assert output_path.exists()
                assert output_path.parent.exists()
            finally:
                # Cleanup
                if template_path.exists():
                    template_path.unlink()

    def test_render_nonexistent_template(self):
        """Test rendering nonexistent template raises error."""
        renderer = TemplateRenderer()
        with pytest.raises(FileNotFoundError):
            renderer.render("nonexistent/template.txt", {})

    def test_get_template_variables(self):
        """Test extracting variables from template."""
        renderer = TemplateRenderer()
        template_content = "{{ var1 }} {{ var2 | default('test') }} {% if var3 %}"

        # Create temporary template
        template_path = renderer.templates_dir / "vars_test.txt"
        template_path.write_text(template_content)

        try:
            variables = renderer.get_template_variables("vars_test.txt")
            assert "var1" in variables
            assert "var2" in variables
            assert "var3" in variables
        finally:
            if template_path.exists():
                template_path.unlink()

    def test_whitespace_handling(self):
        """Test whitespace in template syntax."""
        renderer = TemplateRenderer()
        template = "{{   name   }}"  # Extra whitespace
        result = renderer._render_string(template, {"name": "Test"})
        assert result == "Test"


class TestDetectAppConfig:
    """Test detect_app_config function."""

    def test_default_config(self):
        """Test default configuration detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = Path.cwd()
            try:
                # Change to temp directory
                import os

                os.chdir(tmpdir)

                config = detect_app_config()

                assert "app_name" in config
                assert config["port"] == 8000
                assert config["app_file"] == "app.py"
                assert config["with_database"] is False
                assert config["with_redis"] is False
            finally:
                os.chdir(original_dir)

    def test_detect_server_py(self):
        """Test detection of server.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                # Create server.py
                Path("server.py").touch()

                config = detect_app_config()
                assert config["app_file"] == "server.py"
            finally:
                os.chdir(original_dir)

    def test_detect_main_py(self):
        """Test detection of main.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                # Create main.py
                Path("main.py").touch()

                config = detect_app_config()
                assert config["app_file"] == "main.py"
            finally:
                os.chdir(original_dir)

    def test_detect_database_from_requirements(self):
        """Test database detection from requirements.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                # Create requirements.txt with psycopg2
                Path("requirements.txt").write_text("psycopg2-binary==2.9.0\n")

                config = detect_app_config()
                assert config["with_database"] is True
            finally:
                os.chdir(original_dir)

    def test_detect_redis_from_requirements(self):
        """Test Redis detection from requirements.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                # Create requirements.txt with redis
                Path("requirements.txt").write_text("redis==4.5.0\n")

                config = detect_app_config()
                assert config["with_redis"] is True
            finally:
                os.chdir(original_dir)

    def test_detect_port_from_env(self):
        """Test port detection from .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                # Create .env with PORT
                Path(".env").write_text("PORT=9000\n")

                config = detect_app_config()
                assert config["port"] == 9000
            finally:
                os.chdir(original_dir)
