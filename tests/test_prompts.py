"""
Tests for prompt functionality.
"""

import pytest

from nextmcp import NextMCP, argument, get_prompt_metadata, prompt
from nextmcp.prompts import PromptArgument, PromptRegistry, generate_prompt_docs


class TestPromptDecorator:
    """Test the standalone prompt decorator."""

    def test_basic_prompt(self):
        """Test basic prompt decoration."""

        @prompt()
        def test_prompt(destination: str) -> str:
            return f"Plan trip to {destination}"

        assert test_prompt._prompt_name == "test_prompt"
        assert test_prompt("Paris") == "Plan trip to Paris"

    def test_prompt_with_custom_name(self):
        """Test prompt with custom name."""

        @prompt(name="custom_prompt")
        def test_prompt(city: str) -> str:
            return f"Visit {city}"

        assert test_prompt._prompt_name == "custom_prompt"

    def test_prompt_with_description(self):
        """Test prompt with description."""

        @prompt(description="Plan a vacation")
        def vacation_planner(dest: str) -> str:
            return f"Planning {dest}"

        assert vacation_planner._prompt_description == "Plan a vacation"

    def test_prompt_with_tags(self):
        """Test prompt with tags."""

        @prompt(tags=["travel", "planning"])
        def travel_prompt(dest: str) -> str:
            return f"Travel to {dest}"

        assert travel_prompt._prompt_tags == ["travel", "planning"]

    def test_prompt_with_docstring(self):
        """Test that docstring is used as description."""

        @prompt()
        def documented_prompt(param: str) -> str:
            """This is a documented prompt."""
            return f"Result: {param}"

        assert documented_prompt._prompt_description == "This is a documented prompt."

    def test_async_prompt(self):
        """Test async prompt."""

        @prompt()
        async def async_prompt(param: str) -> str:
            return f"Async: {param}"

        assert async_prompt._prompt_name == "async_prompt"


class TestArgumentDecorator:
    """Test the argument decorator."""

    def test_argument_basic(self):
        """Test basic argument decoration."""

        @prompt()
        @argument("city", description="The destination city")
        def travel_prompt(city: str) -> str:
            return f"Travel to {city}"

        assert hasattr(travel_prompt, "_prompt_arguments")
        assert len(travel_prompt._prompt_arguments) == 1
        assert travel_prompt._prompt_arguments[0].name == "city"

    def test_argument_with_suggestions(self):
        """Test argument with suggestions."""

        @prompt()
        @argument("city", suggestions=["Paris", "Tokyo", "London"])
        def travel_prompt(city: str) -> str:
            return f"Travel to {city}"

        arg = travel_prompt._prompt_arguments[0]
        assert arg.suggestions == ["Paris", "Tokyo", "London"]

    def test_multiple_arguments(self):
        """Test multiple arguments."""

        @prompt()
        @argument("destination", description="Where to go")
        @argument("budget", type="integer", description="Total budget")
        def vacation_prompt(destination: str, budget: int) -> str:
            return f"Plan {destination} with ${budget}"

        assert len(vacation_prompt._prompt_arguments) == 2
        names = [arg.name for arg in vacation_prompt._prompt_arguments]
        assert "destination" in names
        assert "budget" in names

    def test_argument_optional(self):
        """Test optional arguments."""

        @prompt()
        @argument("theme", required=False, default="adventure")
        def themed_prompt(theme: str = "adventure") -> str:
            return f"Theme: {theme}"

        arg = themed_prompt._prompt_arguments[0]
        assert arg.required is False
        assert arg.default == "adventure"


class TestPromptMetadata:
    """Test prompt metadata extraction."""

    def test_get_metadata_basic(self):
        """Test basic metadata extraction."""

        @prompt(description="Test prompt")
        def test_prompt(param: str) -> str:
            return param

        metadata = get_prompt_metadata(test_prompt)
        assert metadata["name"] == "test_prompt"
        assert metadata["description"] == "Test prompt"
        assert "arguments" in metadata

    def test_get_metadata_with_arguments(self):
        """Test metadata extraction with explicit arguments."""

        @prompt()
        @argument("city", description="Destination city", type="string")
        @argument("budget", type="integer", required=True)
        def vacation_prompt(city: str, budget: int) -> str:
            return f"{city}: ${budget}"

        metadata = get_prompt_metadata(vacation_prompt)
        args = metadata["arguments"]
        assert len(args) == 2

        # Check city argument
        city_arg = next(a for a in args if a["name"] == "city")
        assert city_arg["description"] == "Destination city"
        assert city_arg["type"] == "string"

        # Check budget argument
        budget_arg = next(a for a in args if a["name"] == "budget")
        assert budget_arg["type"] == "integer"
        assert budget_arg["required"] is True

    def test_get_metadata_auto_infer(self):
        """Test metadata auto-inference from function signature."""

        @prompt()
        def inferred_prompt(name: str, age: int = 25) -> str:
            return f"{name} is {age}"

        metadata = get_prompt_metadata(inferred_prompt)
        args = metadata["arguments"]

        name_arg = next(a for a in args if a["name"] == "name")
        assert name_arg["type"] == "string"
        assert name_arg["required"] is True

        age_arg = next(a for a in args if a["name"] == "age")
        assert age_arg["type"] == "integer"
        assert age_arg["required"] is False
        assert age_arg["default"] == 25


class TestNextMCPPromptIntegration:
    """Test prompt integration with NextMCP app."""

    def test_app_prompt_registration(self):
        """Test prompt registration with app."""
        app = NextMCP("test-app")

        @app.prompt()
        def test_prompt(param: str) -> str:
            return f"Result: {param}"

        assert "test_prompt" in app.get_prompts()

    def test_app_prompt_custom_name(self):
        """Test prompt with custom name."""
        app = NextMCP("test-app")

        @app.prompt(name="custom_name")
        def test_prompt(param: str) -> str:
            return param

        prompts = app.get_prompts()
        assert "custom_name" in prompts
        assert "test_prompt" not in prompts

    def test_app_prompt_middleware(self):
        """Test that middleware is applied to prompts."""
        app = NextMCP("test-app")

        # Add middleware that wraps the function
        def uppercase_middleware(fn):
            def wrapper(*args, **kwargs):
                result = fn(*args, **kwargs)
                return result.upper() if isinstance(result, str) else result

            return wrapper

        app.add_middleware(uppercase_middleware)

        @app.prompt()
        def test_prompt(text: str) -> str:
            return text

        result = test_prompt("hello")
        assert result == "HELLO"

    def test_app_async_prompt(self):
        """Test async prompt registration."""
        app = NextMCP("test-app")

        @app.prompt()
        async def async_prompt(param: str) -> str:
            return f"Async: {param}"

        prompts = app.get_prompts()
        assert "async_prompt" in prompts
        prompt_fn = prompts["async_prompt"]
        assert prompt_fn._is_async is True

    def test_app_prompt_completion(self):
        """Test prompt completion registration."""
        app = NextMCP("test-app")

        @app.prompt()
        def travel_prompt(city: str) -> str:
            return f"Travel to {city}"

        @app.prompt_completion("travel_prompt", "city")
        def complete_cities(partial: str) -> list[str]:
            cities = ["Paris", "Tokyo", "London"]
            return [c for c in cities if partial.lower() in c.lower()]

        # Check completion is registered
        key = "travel_prompt.city"
        assert key in app._prompt_completions
        assert app._prompt_completions[key]("par") == ["Paris"]

    def test_multiple_prompts(self):
        """Test registering multiple prompts."""
        app = NextMCP("test-app")

        @app.prompt()
        def prompt1(x: str) -> str:
            return x

        @app.prompt()
        def prompt2(y: str) -> str:
            return y

        @app.prompt()
        def prompt3(z: str) -> str:
            return z

        prompts = app.get_prompts()
        assert len(prompts) == 3
        assert "prompt1" in prompts
        assert "prompt2" in prompts
        assert "prompt3" in prompts


class TestPromptRegistry:
    """Test PromptRegistry functionality."""

    def test_registry_basic(self):
        """Test basic registry operations."""
        registry = PromptRegistry()

        @prompt()
        def test_prompt(param: str) -> str:
            return param

        registry.register(test_prompt)
        assert registry.get("test_prompt") is test_prompt

    def test_registry_with_namespace(self):
        """Test registry with namespaces."""
        registry = PromptRegistry()

        @prompt(name="plan")
        def travel_plan(dest: str) -> str:
            return f"Plan {dest}"

        registry.register(travel_plan, namespace="travel")

        # Check it's in namespace
        ns_prompts = registry.get_namespace("travel")
        assert "plan" in ns_prompts

        # Check full name
        assert registry.get("travel.plan") is travel_plan

    def test_registry_all(self):
        """Test getting all prompts."""
        registry = PromptRegistry()

        @prompt()
        def prompt1(x: str) -> str:
            return x

        @prompt()
        def prompt2(y: str) -> str:
            return y

        registry.register(prompt1)
        registry.register(prompt2)

        all_prompts = registry.all()
        assert len(all_prompts) == 2
        assert "prompt1" in all_prompts
        assert "prompt2" in all_prompts

    def test_registry_completion(self):
        """Test completion registration."""
        registry = PromptRegistry()

        def complete_cities(partial: str) -> list[str]:
            return ["Paris", "Tokyo"]

        registry.register_completion("travel_prompt", "city", complete_cities)

        completion_fn = registry.get_completion("travel_prompt", "city")
        assert completion_fn is complete_cities


class TestPromptDocumentation:
    """Test prompt documentation generation."""

    def test_generate_docs_basic(self):
        """Test basic documentation generation."""

        @prompt(description="Plan a trip")
        def travel_prompt(destination: str) -> str:
            return f"Planning {destination}"

        prompts = {"travel_prompt": travel_prompt}
        docs = generate_prompt_docs(prompts)

        assert "MCP Prompts Documentation" in docs
        assert "travel_prompt" in docs
        assert "Plan a trip" in docs

    def test_generate_docs_with_arguments(self):
        """Test documentation with arguments."""

        @prompt()
        @argument("city", description="Destination city", suggestions=["Paris", "Tokyo"])
        @argument("budget", type="integer", description="Budget in USD")
        def vacation_prompt(city: str, budget: int) -> str:
            return f"{city}: ${budget}"

        prompts = {"vacation_prompt": vacation_prompt}
        docs = generate_prompt_docs(prompts)

        assert "city" in docs
        assert "budget" in docs
        assert "Destination city" in docs
        assert "Budget in USD" in docs
        assert "Paris" in docs
        assert "Tokyo" in docs

    def test_generate_docs_with_tags(self):
        """Test documentation with tags."""

        @prompt(tags=["travel", "planning"])
        def tagged_prompt(dest: str) -> str:
            return f"Plan {dest}"

        prompts = {"tagged_prompt": tagged_prompt}
        docs = generate_prompt_docs(prompts)

        assert "Tags" in docs or "tags" in docs.lower()
        assert "travel" in docs
        assert "planning" in docs


class TestPromptArgument:
    """Test PromptArgument class."""

    def test_argument_creation(self):
        """Test creating a PromptArgument."""
        arg = PromptArgument(
            name="city",
            description="Destination city",
            type="string",
            required=True,
            suggestions=["Paris", "Tokyo"],
        )

        assert arg.name == "city"
        assert arg.description == "Destination city"
        assert arg.type == "string"
        assert arg.required is True
        assert arg.suggestions == ["Paris", "Tokyo"]

    def test_argument_to_dict(self):
        """Test converting argument to dictionary."""
        arg = PromptArgument(
            name="budget", description="Total budget", type="integer", required=False, default=1000
        )

        arg_dict = arg.to_dict()
        assert arg_dict["name"] == "budget"
        assert arg_dict["description"] == "Total budget"
        assert arg_dict["type"] == "integer"
        assert arg_dict["required"] is False
        assert arg_dict["default"] == 1000

    def test_argument_defaults(self):
        """Test default values for PromptArgument."""
        arg = PromptArgument(name="test")

        assert arg.type == "string"
        assert arg.required is True
        assert arg.default is None
        assert arg.suggestions == []
        assert arg.suggestions_fn is None


@pytest.mark.asyncio
async def test_async_prompt_execution():
    """Test that async prompts can be executed."""

    @prompt()
    async def async_prompt(message: str) -> str:
        return f"Processed: {message}"

    result = await async_prompt("test")
    assert result == "Processed: test"


def test_prompt_preserves_original_function():
    """Test that original function behavior is preserved."""

    @prompt()
    def calculator_prompt(a: int, b: int) -> str:
        return f"Calculate: {a} + {b} = {a + b}"

    result = calculator_prompt(5, 3)
    assert "5 + 3 = 8" in result
