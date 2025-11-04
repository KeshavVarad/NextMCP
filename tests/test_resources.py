"""
Tests for resource functionality.
"""

import pytest

from nextmcp import NextMCP, get_resource_metadata, resource, resource_template
from nextmcp.resources import (
    ResourceMetadata,
    ResourceRegistry,
    ResourceTemplate,
    generate_resource_docs,
)


class TestResourceDecorator:
    """Test the standalone resource decorator."""

    def test_basic_resource(self):
        """Test basic resource decoration."""

        @resource("file:///test.txt")
        def test_resource() -> str:
            return "test content"

        assert test_resource._resource_uri == "file:///test.txt"
        assert test_resource() == "test content"

    def test_resource_with_name(self):
        """Test resource with custom name."""

        @resource("config://app", name="App Config")
        def app_config() -> dict:
            return {"key": "value"}

        metadata = app_config._resource_metadata
        assert metadata.name == "App Config"

    def test_resource_with_description(self):
        """Test resource with description."""

        @resource("file:///logs/app.log", description="Application logs")
        def app_logs() -> str:
            return "log content"

        metadata = app_logs._resource_metadata
        assert metadata.description == "Application logs"

    def test_resource_with_mime_type(self):
        """Test resource with explicit MIME type."""

        @resource("data://json", mime_type="application/json")
        def json_data() -> dict:
            return {"data": "value"}

        metadata = json_data._resource_metadata
        assert metadata.mime_type == "application/json"

    def test_resource_subscribable(self):
        """Test subscribable resource."""

        @resource("file:///config.json", subscribable=True)
        def config() -> dict:
            return {"setting": "value"}

        metadata = config._resource_metadata
        assert metadata.subscribable is True

    def test_resource_mime_detection(self):
        """Test automatic MIME type detection."""

        @resource("file:///document.pdf")
        def pdf_doc() -> bytes:
            return b"PDF content"

        metadata = pdf_doc._resource_metadata
        assert "pdf" in metadata.mime_type.lower() or metadata.mime_type == "application/pdf"

    def test_async_resource(self):
        """Test async resource."""

        @resource("db://users")
        async def users() -> list:
            return [{"name": "Alice"}, {"name": "Bob"}]

        assert users._resource_uri == "db://users"


class TestResourceTemplate:
    """Test resource template functionality."""

    def test_template_basic(self):
        """Test basic template decoration."""

        @resource_template("weather://{city}")
        def weather(city: str) -> dict:
            return {"city": city, "temp": 72}

        template = weather._resource_template
        assert template.uri_pattern == "weather://{city}"
        assert "city" in template.parameters

    def test_template_multiple_params(self):
        """Test template with multiple parameters."""

        @resource_template("file:///docs/{category}/{filename}")
        def docs(category: str, filename: str) -> str:
            return f"Content of {category}/{filename}"

        template = docs._resource_template
        assert template.parameters == ["category", "filename"]

    def test_template_matches_uri(self):
        """Test URI matching."""
        template = ResourceTemplate("weather://{city}/{date}")

        assert template.matches("weather://London/2025-01-01") is True
        assert template.matches("weather://Paris/2025-12-31") is True
        assert template.matches("other://London/2025-01-01") is False
        assert template.matches("weather://London") is False

    def test_template_extract_params(self):
        """Test parameter extraction."""
        template = ResourceTemplate("file:///docs/{category}/{file}")

        params = template.extract_parameters("file:///docs/api/auth.md")
        assert params == {"category": "api", "file": "auth.md"}

        params = template.extract_parameters("file:///docs/guides/quickstart.md")
        assert params == {"category": "guides", "file": "quickstart.md"}

    def test_template_with_description(self):
        """Test template with description."""

        @resource_template("db://table/{table_name}", description="Database table access")
        def db_table(table_name: str) -> list:
            return []

        template = db_table._resource_template
        assert template.description == "Database table access"

    def test_async_template(self):
        """Test async resource template."""

        @resource_template("api://endpoint/{path}")
        async def api_data(path: str) -> dict:
            return {"path": path, "data": "value"}

        assert hasattr(api_data, "_resource_template")


class TestResourceMetadata:
    """Test ResourceMetadata class."""

    def test_metadata_creation(self):
        """Test creating ResourceMetadata."""
        metadata = ResourceMetadata(
            uri="file:///test.txt",
            name="Test File",
            description="A test file",
            mime_type="text/plain",
            subscribable=True,
            max_subscribers=50,
        )

        assert metadata.uri == "file:///test.txt"
        assert metadata.name == "Test File"
        assert metadata.description == "A test file"
        assert metadata.mime_type == "text/plain"
        assert metadata.subscribable is True
        assert metadata.max_subscribers == 50

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = ResourceMetadata(
            uri="config://app", name="Config", description="App configuration", subscribable=False
        )

        meta_dict = metadata.to_dict()
        assert meta_dict["uri"] == "config://app"
        assert meta_dict["name"] == "Config"
        assert meta_dict["description"] == "App configuration"
        assert meta_dict["subscribable"] is False

    def test_metadata_defaults(self):
        """Test default values."""
        metadata = ResourceMetadata(uri="file:///test.txt")

        assert metadata.name == "file:///test.txt"  # Uses URI as default name
        assert metadata.description is None
        assert metadata.subscribable is False
        assert metadata.max_subscribers == 100


class TestResourceTemplateClass:
    """Test ResourceTemplate class."""

    def test_template_creation(self):
        """Test creating a ResourceTemplate."""
        template = ResourceTemplate(
            uri_pattern="weather://{city}/{date}", description="Weather forecast"
        )

        assert template.uri_pattern == "weather://{city}/{date}"
        assert template.description == "Weather forecast"
        assert template.parameters == ["city", "date"]

    def test_template_to_dict(self):
        """Test converting template to dictionary."""
        template = ResourceTemplate(uri_pattern="file:///{path}", description="File access")

        template_dict = template.to_dict()
        assert template_dict["uriTemplate"] == "file:///{path}"
        assert template_dict["description"] == "File access"
        assert template_dict["parameters"] == ["path"]

    def test_template_complex_pattern(self):
        """Test complex URI patterns."""
        template = ResourceTemplate("api://v{version}/{resource}/{id}")

        assert template.parameters == ["version", "resource", "id"]
        assert template.matches("api://v1/users/123") is True


class TestNextMCPResourceIntegration:
    """Test resource integration with NextMCP app."""

    def test_app_resource_registration(self):
        """Test resource registration with app."""
        app = NextMCP("test-app")

        @app.resource("file:///test.txt")
        def test_resource() -> str:
            return "content"

        resources = app.get_resources()
        assert "file:///test.txt" in resources

    def test_app_resource_middleware(self):
        """Test that middleware is applied to resources."""
        app = NextMCP("test-app")

        # Add middleware
        def uppercase_middleware(fn):
            def wrapper(*args, **kwargs):
                result = fn(*args, **kwargs)
                return result.upper() if isinstance(result, str) else result

            return wrapper

        app.add_middleware(uppercase_middleware)

        @app.resource("data://test")
        def test_resource() -> str:
            return "hello"

        result = test_resource()
        assert result == "HELLO"

    def test_app_async_resource(self):
        """Test async resource registration."""
        app = NextMCP("test-app")

        @app.resource("db://data")
        async def async_resource() -> dict:
            return {"data": "value"}

        resources = app.get_resources()
        assert "db://data" in resources
        resource_fn = resources["db://data"]
        assert resource_fn._is_async is True

    def test_app_resource_template(self):
        """Test resource template registration."""
        app = NextMCP("test-app")

        @app.resource_template("weather://{city}")
        def weather(city: str) -> dict:
            return {"city": city}

        templates = app.get_resource_templates()
        assert "weather://{city}" in templates

    def test_multiple_resources(self):
        """Test registering multiple resources."""
        app = NextMCP("test-app")

        @app.resource("file:///log1.txt")
        def log1() -> str:
            return "log1"

        @app.resource("file:///log2.txt")
        def log2() -> str:
            return "log2"

        @app.resource("config://app")
        def config() -> dict:
            return {}

        resources = app.get_resources()
        assert len(resources) == 3

    def test_app_template_completion(self):
        """Test template completion registration."""
        app = NextMCP("test-app")

        @app.resource_template("docs://{category}")
        def docs(category: str) -> str:
            return f"Docs for {category}"

        @app.template_completion("docs", "category")
        def complete_categories(partial: str) -> list[str]:
            categories = ["api", "guides", "tutorials"]
            return [c for c in categories if partial in c]

        key = "docs.category"
        assert key in app._template_completions


class TestResourceSubscriptions:
    """Test resource subscription functionality."""

    def test_subscribe_to_resource(self):
        """Test subscribing to a resource."""
        app = NextMCP("test-app")

        @app.resource("file:///config.json", subscribable=True)
        def config() -> dict:
            return {"setting": "value"}

        # Subscribe
        success = app.subscribe_to_resource("file:///config.json", "subscriber1")
        assert success is True

    def test_subscribe_non_subscribable(self):
        """Test subscribing to non-subscribable resource fails."""
        app = NextMCP("test-app")

        @app.resource("data://static", subscribable=False)
        def static_data() -> str:
            return "static"

        success = app.subscribe_to_resource("data://static", "subscriber1")
        assert success is False

    def test_subscribe_nonexistent_resource(self):
        """Test subscribing to nonexistent resource fails."""
        app = NextMCP("test-app")

        success = app.subscribe_to_resource("nonexistent://resource", "subscriber1")
        assert success is False

    def test_unsubscribe_from_resource(self):
        """Test unsubscribing from a resource."""
        app = NextMCP("test-app")

        @app.resource("file:///data.json", subscribable=True)
        def data() -> dict:
            return {}

        # Subscribe then unsubscribe
        app.subscribe_to_resource("file:///data.json", "subscriber1")
        success = app.unsubscribe_from_resource("file:///data.json", "subscriber1")
        assert success is True

    def test_max_subscribers_limit(self):
        """Test max subscribers limit enforcement."""
        app = NextMCP("test-app")

        @app.resource("file:///limited.json", subscribable=True, max_subscribers=2)
        def limited() -> dict:
            return {}

        # Subscribe up to limit
        app.subscribe_to_resource("file:///limited.json", "sub1")
        app.subscribe_to_resource("file:///limited.json", "sub2")

        # Third subscription should remove oldest
        app.subscribe_to_resource("file:///limited.json", "sub3")

        # Check subscribers
        subscribers = app._resource_subscriptions["file:///limited.json"]
        assert len(subscribers) == 2
        assert "sub1" not in subscribers  # Oldest removed
        assert "sub2" in subscribers
        assert "sub3" in subscribers

    def test_notify_resource_changed(self):
        """Test notifying resource changes."""
        app = NextMCP("test-app")

        @app.resource("file:///watched.json", subscribable=True)
        def watched() -> dict:
            return {}

        # Subscribe multiple subscribers
        app.subscribe_to_resource("file:///watched.json", "sub1")
        app.subscribe_to_resource("file:///watched.json", "sub2")

        # Notify
        count = app.notify_resource_changed("file:///watched.json")
        assert count == 2

    def test_notify_no_subscribers(self):
        """Test notifying resource with no subscribers."""
        app = NextMCP("test-app")

        @app.resource("file:///unwatched.json", subscribable=True)
        def unwatched() -> dict:
            return {}

        count = app.notify_resource_changed("file:///unwatched.json")
        assert count == 0


class TestResourceRegistry:
    """Test ResourceRegistry functionality."""

    def test_registry_register_resource(self):
        """Test registering a resource."""
        registry = ResourceRegistry()

        @resource("file:///test.txt")
        def test_res() -> str:
            return "content"

        registry.register_resource(test_res)
        assert registry.get_resource("file:///test.txt") is test_res

    def test_registry_register_template(self):
        """Test registering a template."""
        registry = ResourceRegistry()

        @resource_template("weather://{city}")
        def weather(city: str) -> dict:
            return {"city": city}

        registry.register_template(weather)
        assert registry.get_template("weather://{city}") is weather

    def test_registry_find_template_for_uri(self):
        """Test finding matching template for URI."""
        registry = ResourceRegistry()

        @resource_template("file:///docs/{category}/{file}")
        def docs(category: str, file: str) -> str:
            return f"{category}/{file}"

        registry.register_template(docs)

        result = registry.find_template_for_uri("file:///docs/api/auth.md")
        assert result is not None
        template_fn, params = result
        assert template_fn is docs
        assert params == {"category": "api", "file": "auth.md"}

    def test_registry_subscribe(self):
        """Test subscription through registry."""
        registry = ResourceRegistry()

        @resource("file:///config.json", subscribable=True)
        def config() -> dict:
            return {}

        registry.register_resource(config)

        success = registry.subscribe("file:///config.json", "sub1")
        assert success is True

        subscribers = registry.get_subscribers("file:///config.json")
        assert "sub1" in subscribers

    def test_registry_all_resources(self):
        """Test getting all resources."""
        registry = ResourceRegistry()

        @resource("file:///a.txt")
        def res_a() -> str:
            return "a"

        @resource("file:///b.txt")
        def res_b() -> str:
            return "b"

        registry.register_resource(res_a)
        registry.register_resource(res_b)

        all_res = registry.all_resources()
        assert len(all_res) == 2
        assert "file:///a.txt" in all_res
        assert "file:///b.txt" in all_res

    def test_registry_all_templates(self):
        """Test getting all templates."""
        registry = ResourceRegistry()

        @resource_template("weather://{city}")
        def weather(city: str) -> dict:
            return {}

        @resource_template("docs://{path}")
        def docs(path: str) -> str:
            return ""

        registry.register_template(weather)
        registry.register_template(docs)

        all_templates = registry.all_templates()
        assert len(all_templates) == 2
        assert "weather://{city}" in all_templates
        assert "docs://{path}" in all_templates


class TestResourceDocumentation:
    """Test resource documentation generation."""

    def test_generate_docs_resources(self):
        """Test documentation for direct resources."""

        @resource("file:///app.log", description="Application logs")
        def app_log() -> str:
            return "logs"

        resources = {"file:///app.log": app_log}
        docs = generate_resource_docs(resources)

        assert "MCP Resources Documentation" in docs
        assert "file:///app.log" in docs
        assert "Application logs" in docs

    def test_generate_docs_templates(self):
        """Test documentation for templates."""

        @resource_template("weather://{city}/{date}", description="Weather forecast")
        def weather(city: str, date: str) -> dict:
            return {}

        templates = {"weather://{city}/{date}": weather}
        docs = generate_resource_docs({}, templates)

        assert "Resource Templates" in docs
        assert "weather://{city}/{date}" in docs
        assert "Weather forecast" in docs
        assert "city" in docs
        assert "date" in docs

    def test_generate_docs_both(self):
        """Test documentation for both resources and templates."""

        @resource("config://app", description="App config")
        def config() -> dict:
            return {}

        @resource_template("docs://{category}", description="Documentation")
        def docs(category: str) -> str:
            return ""

        resources = {"config://app": config}
        templates = {"docs://{category}": docs}
        docs_str = generate_resource_docs(resources, templates)

        assert "Direct Resources" in docs_str
        assert "Resource Templates" in docs_str
        assert "config://app" in docs_str
        assert "docs://{category}" in docs_str


@pytest.mark.asyncio
async def test_async_resource_execution():
    """Test that async resources can be executed."""

    @resource("db://async_data")
    async def async_data() -> dict:
        return {"data": "async value"}

    result = await async_data()
    assert result == {"data": "async value"}


def test_resource_metadata_extraction():
    """Test extracting metadata from resources."""

    @resource(
        "file:///test.json", name="Test", description="Test resource", mime_type="application/json"
    )
    def test_res() -> dict:
        return {}

    metadata = get_resource_metadata(test_res)
    assert metadata["type"] == "direct"
    assert metadata["uri"] == "file:///test.json"
    assert metadata["name"] == "Test"
    assert metadata["description"] == "Test resource"
    assert metadata["mimeType"] == "application/json"


def test_template_metadata_extraction():
    """Test extracting metadata from templates."""

    @resource_template("api://{endpoint}/{id}", description="API access")
    def api_template(endpoint: str, id: str) -> dict:
        return {}

    metadata = get_resource_metadata(api_template)
    assert metadata["type"] == "template"
    assert metadata["uriTemplate"] == "api://{endpoint}/{id}"
    assert metadata["description"] == "API access"
    assert metadata["parameters"] == ["endpoint", "id"]
