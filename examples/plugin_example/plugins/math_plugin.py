"""
Math Plugin - Example plugin that adds mathematical tools.

This demonstrates:
- Creating a plugin class
- Registering multiple tools
- Using type hints and docstrings
"""

from nextmcp import Plugin


class MathPlugin(Plugin):
    """Plugin providing mathematical operations."""

    name = "math-plugin"
    version = "1.0.0"
    description = "Provides mathematical operation tools"
    author = "NextMCP Examples"

    def on_load(self, app):
        """Register math tools with the application."""

        @app.tool(description="Add two numbers")
        def add(a: float, b: float) -> float:
            """
            Add two numbers together.

            Args:
                a: First number
                b: Second number

            Returns:
                Sum of a and b
            """
            return a + b

        @app.tool(description="Multiply two numbers")
        def multiply(a: float, b: float) -> float:
            """
            Multiply two numbers.

            Args:
                a: First number
                b: Second number

            Returns:
                Product of a and b
            """
            return a * b

        @app.tool(description="Calculate power")
        def power(base: float, exponent: float) -> float:
            """
            Calculate base raised to the exponent.

            Args:
                base: Base number
                exponent: Exponent

            Returns:
                base^exponent
            """
            return base**exponent

        print(f"✓ {self.name} loaded: Added 3 math tools")
