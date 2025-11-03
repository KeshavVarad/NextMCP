"""
String Plugin - Example plugin with string manipulation tools.

This demonstrates:
- Plugin with multiple related tools
- Working with string data
- Plugin dependencies (optional)
"""

from nextmcp import Plugin


class StringPlugin(Plugin):
    """Plugin providing string manipulation tools."""

    name = "string-plugin"
    version = "1.0.0"
    description = "Provides string manipulation tools"
    author = "NextMCP Examples"

    def on_load(self, app):
        """Register string tools with the application."""

        @app.tool()
        def uppercase(text: str) -> str:
            """
            Convert text to uppercase.

            Args:
                text: Input text

            Returns:
                Uppercase text
            """
            return text.upper()

        @app.tool()
        def lowercase(text: str) -> str:
            """
            Convert text to lowercase.

            Args:
                text: Input text

            Returns:
                Lowercase text
            """
            return text.lower()

        @app.tool()
        def reverse(text: str) -> str:
            """
            Reverse a string.

            Args:
                text: Input text

            Returns:
                Reversed text
            """
            return text[::-1]

        @app.tool()
        def count_words(text: str) -> int:
            """
            Count words in text.

            Args:
                text: Input text

            Returns:
                Number of words
            """
            return len(text.split())

        print(f"✓ {self.name} loaded: Added 4 string tools")
