"""
CLI commands for NextMCP using Typer.

Provides commands for:
- Initializing new projects
- Running MCP servers
- Generating documentation
"""

import logging
import shutil
import sys
from pathlib import Path

try:
    import typer
    from rich.console import Console
    from rich.syntax import Syntax
except ImportError:
    typer = None
    Console = None
    Syntax = None

logger = logging.getLogger(__name__)

# Create CLI app if typer is available
if typer:
    app = typer.Typer(
        name="nextmcp",
        help="NextMCP - Production-grade MCP server toolkit",
        add_completion=False,
    )
    console = Console() if Console else None
else:
    app = None
    console = None


def get_template_dir() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent / "templates"


def get_examples_dir() -> Path:
    """Get the path to the examples directory."""
    # Go up one level from nextmcp package to root
    return Path(__file__).parent.parent / "examples"


if app:

    @app.command()
    def init(
        name: str = typer.Argument(..., help="Name of the new project"),
        template: str = typer.Option(
            "weather_bot", "--template", "-t", help="Template to use (default: weather_bot)"
        ),
        path: str | None = typer.Option(
            None, "--path", "-p", help="Custom path for the project (default: ./<name>)"
        ),
    ):
        """
        Initialize a new NextMCP project from a template.

        Creates a new directory with boilerplate code to get started quickly.

        Example:
            mcp init my-bot
            mcp init my-bot --template weather_bot
        """
        try:
            # Determine target path
            target_path = Path(path) if path else Path(name)

            # Check if directory already exists
            if target_path.exists():
                if console:
                    console.print(f"[red]Error:[/red] Directory {target_path} already exists")
                else:
                    print(f"Error: Directory {target_path} already exists")
                raise typer.Exit(code=1)

            # Get template source
            examples_dir = get_examples_dir()
            template_source = examples_dir / template

            if not template_source.exists():
                if console:
                    console.print(f"[red]Error:[/red] Template '{template}' not found")
                    console.print(f"Available templates in: {examples_dir}")
                else:
                    print(f"Error: Template '{template}' not found")
                raise typer.Exit(code=1)

            # Copy template to target
            shutil.copytree(template_source, target_path)

            if console:
                console.print(f"[green]✓[/green] Created new project: {target_path}")
                console.print("\nNext steps:")
                console.print(f"  cd {target_path}")
                console.print("  pip install -r requirements.txt  # if present")
                console.print("  mcp run app.py")
            else:
                print(f"✓ Created new project: {target_path}")
                print("\nNext steps:")
                print(f"  cd {target_path}")
                print("  pip install -r requirements.txt")
                print("  mcp run app.py")

        except Exception as e:
            if console:
                console.print(f"[red]Error:[/red] {e}")
            else:
                print(f"Error: {e}")
            raise typer.Exit(code=1) from e

    @app.command()
    def run(
        app_file: str = typer.Argument(
            "app.py", help="Python file containing the NextMCP application"
        ),
        host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
        port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
        reload: bool = typer.Option(
            False, "--reload", "-r", help="Enable auto-reload on file changes"
        ),
    ):
        """
        Run a NextMCP application.

        Example:
            mcp run app.py
            mcp run app.py --host 0.0.0.0 --port 8080
            mcp run app.py --reload
        """
        try:
            app_path = Path(app_file)

            if not app_path.exists():
                if console:
                    console.print(f"[red]Error:[/red] File not found: {app_file}")
                else:
                    print(f"Error: File not found: {app_file}")
                raise typer.Exit(code=1)

            if console:
                console.print("[blue]Starting NextMCP server...[/blue]")
                console.print(f"  File: {app_file}")
                console.print(f"  Host: {host}")
                console.print(f"  Port: {port}")
                console.print(f"  Reload: {reload}")
                console.print()

            # Set environment variables for the app to use
            import os

            os.environ["MCP_HOST"] = host
            os.environ["MCP_PORT"] = str(port)

            # Execute the app file
            with open(app_path) as f:
                code = f.read()

            # Create a namespace for execution
            namespace = {"__name__": "__main__", "__file__": str(app_path.absolute())}

            # Execute the code
            exec(code, namespace)

        except Exception as e:
            if console:
                console.print(f"[red]Error:[/red] {e}")
            else:
                print(f"Error: {e}")
            raise typer.Exit(code=1) from e

    @app.command()
    def docs(
        app_file: str = typer.Argument(
            "app.py", help="Python file containing the NextMCP application"
        ),
        output: str | None = typer.Option(
            None, "--output", "-o", help="Output file for documentation (default: stdout)"
        ),
        format: str = typer.Option(
            "markdown", "--format", "-f", help="Output format: markdown, json"
        ),
    ):
        """
        Generate documentation for MCP tools.

        Example:
            mcp docs app.py
            mcp docs app.py --output docs.md
            mcp docs app.py --format json
        """
        try:
            from nextmcp.tools import generate_tool_docs

            app_path = Path(app_file)

            if not app_path.exists():
                if console:
                    console.print(f"[red]Error:[/red] File not found: {app_file}")
                else:
                    print(f"Error: File not found: {app_file}")
                raise typer.Exit(code=1)

            # Load the app file
            with open(app_path) as f:
                code = f.read()

            namespace = {}
            exec(code, namespace)

            # Find NextMCP instance in namespace
            app_instance = None
            for value in namespace.values():
                if hasattr(value, "_tools"):  # Duck typing for NextMCP
                    app_instance = value
                    break

            if not app_instance:
                if console:
                    console.print("[yellow]Warning:[/yellow] No NextMCP instance found in app file")
                else:
                    print("Warning: No NextMCP instance found in app file")
                raise typer.Exit(code=1)

            # Generate documentation
            if format == "markdown":
                doc_content = generate_tool_docs(app_instance._tools)
            elif format == "json":
                import json

                from nextmcp.tools import get_tool_metadata

                tools_metadata = {
                    name: get_tool_metadata(fn) for name, fn in app_instance._tools.items()
                }
                doc_content = json.dumps(tools_metadata, indent=2)
            else:
                if console:
                    console.print(f"[red]Error:[/red] Unknown format: {format}")
                else:
                    print(f"Error: Unknown format: {format}")
                raise typer.Exit(code=1)

            # Output documentation
            if output:
                Path(output).write_text(doc_content)
                if console:
                    console.print(f"[green]✓[/green] Documentation written to {output}")
                else:
                    print(f"✓ Documentation written to {output}")
            else:
                print(doc_content)

        except Exception as e:
            if console:
                console.print(f"[red]Error:[/red] {e}")
            else:
                print(f"Error: {e}")
            raise typer.Exit(code=1) from e

    @app.command()
    def version():
        """Show NextMCP version information."""
        try:
            from nextmcp import __version__

            version_str = __version__
        except ImportError:
            version_str = "unknown"

        if console:
            console.print(f"NextMCP version: {version_str}")
        else:
            print(f"NextMCP version: {version_str}")


def main():
    """Entry point for the CLI."""
    if app is None:
        print("Error: typer is not installed. Install with: pip install typer rich")
        sys.exit(1)

    app()


if __name__ == "__main__":
    main()
