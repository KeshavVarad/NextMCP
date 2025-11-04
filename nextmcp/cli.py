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
        name: str = typer.Argument(
            None, help="Name of the new project (required for template init)"
        ),
        template: str = typer.Option(
            "weather_bot", "--template", "-t", help="Template to use (default: weather_bot)"
        ),
        path: str | None = typer.Option(
            None, "--path", "-p", help="Custom path for the project (default: ./<name>)"
        ),
        docker: bool = typer.Option(
            False, "--docker", "-d", help="Generate Docker deployment files in current directory"
        ),
        with_database: bool = typer.Option(
            False, "--with-database", help="Include PostgreSQL in docker-compose.yml"
        ),
        with_redis: bool = typer.Option(
            False, "--with-redis", help="Include Redis in docker-compose.yml"
        ),
        port: int = typer.Option(8000, "--port", help="Port for the application"),
    ):
        """
        Initialize a new NextMCP project from a template or generate Docker files.

        Examples:
            mcp init my-bot                    # Create new project from template
            mcp init my-bot --template weather_bot
            mcp init --docker                  # Generate Docker files in current dir
            mcp init --docker --with-database  # Include PostgreSQL
        """
        try:
            # Docker file generation mode
            if docker:
                from nextmcp.deployment.templates import TemplateRenderer, detect_app_config

                renderer = TemplateRenderer()

                # Auto-detect or use provided config
                config = detect_app_config()
                config["port"] = port
                config["with_database"] = with_database
                config["with_redis"] = with_redis

                # If name is provided, use it
                if name:
                    config["app_name"] = name

                if console:
                    console.print("[blue]Generating Docker deployment files...[/blue]")
                    console.print(f"  App name: {config['app_name']}")
                    console.print(f"  Port: {config['port']}")
                    console.print(f"  App file: {config['app_file']}")
                    if with_database:
                        console.print("  ✓ Including PostgreSQL")
                    if with_redis:
                        console.print("  ✓ Including Redis")
                    console.print()

                # Render templates
                renderer.render_to_file("docker/Dockerfile.template", "Dockerfile", config)
                renderer.render_to_file(
                    "docker/docker-compose.yml.template", "docker-compose.yml", config
                )
                renderer.render_to_file("docker/.dockerignore.template", ".dockerignore", config)

                if console:
                    console.print("[green]✓[/green] Generated Docker files:")
                    console.print("  - Dockerfile")
                    console.print("  - docker-compose.yml")
                    console.print("  - .dockerignore")
                    console.print("\nNext steps:")
                    console.print("  docker compose up --build")
                    console.print(f"  Open: http://localhost:{config['port']}/health")
                else:
                    print("✓ Generated Docker files: Dockerfile, docker-compose.yml, .dockerignore")
                    print("\nNext steps:")
                    print("  docker compose up --build")
                    print(f"  Open: http://localhost:{config['port']}/health")

                return

            # Template-based project initialization mode
            if not name:
                if console:
                    console.print(
                        "[red]Error:[/red] Project name is required for template initialization"
                    )
                    console.print("Use: mcp init <name> or mcp init --docker for Docker files only")
                else:
                    print("Error: Project name is required")
                raise typer.Exit(code=1)

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

    @app.command()
    def deploy(
        platform: str = typer.Option(
            None, "--platform", "-p", help="Platform to deploy to (docker, railway, render, fly)"
        ),
        build: bool = typer.Option(True, "--build/--no-build", help="Build before deploying"),
    ):
        """
        Deploy NextMCP application to a platform.

        Supports:
        - docker: Build and run with Docker
        - railway: Deploy to Railway (requires railway CLI)
        - render: Deploy to Render (requires render CLI)
        - fly: Deploy to Fly.io (requires flyctl)

        Examples:
            mcp deploy                  # Auto-detect and deploy
            mcp deploy --platform docker
            mcp deploy --platform railway
        """
        try:
            import subprocess

            # Auto-detect platform if not specified
            if not platform:
                if Path("Dockerfile").exists():
                    platform = "docker"
                elif Path("railway.json").exists() or Path("railway.toml").exists():
                    platform = "railway"
                elif Path("render.yaml").exists():
                    platform = "render"
                elif Path("fly.toml").exists():
                    platform = "fly"
                else:
                    if console:
                        console.print("[yellow]No platform detected.[/yellow]")
                        console.print("Generate deployment files with: mcp init --docker")
                    else:
                        print("No platform detected. Generate files with: mcp init --docker")
                    raise typer.Exit(code=1)

                if console:
                    console.print(f"[blue]Auto-detected platform:[/blue] {platform}")

            # Docker deployment
            if platform == "docker":
                if not Path("Dockerfile").exists():
                    if console:
                        console.print("[red]Error:[/red] Dockerfile not found")
                        console.print("Generate with: mcp init --docker")
                    else:
                        print("Error: Dockerfile not found. Generate with: mcp init --docker")
                    raise typer.Exit(code=1)

                if console:
                    console.print("[blue]Deploying with Docker...[/blue]")

                if build:
                    if console:
                        console.print("Building Docker image...")
                    subprocess.run(["docker", "compose", "build"], check=True)

                if console:
                    console.print("Starting containers...")
                subprocess.run(["docker", "compose", "up", "-d"], check=True)

                if console:
                    console.print("[green]✓[/green] Deployed successfully!")
                    console.print("\nView logs: docker compose logs -f")
                    console.print("Stop: docker compose down")
                else:
                    print("✓ Deployed successfully!")
                    print("View logs: docker compose logs -f")

            # Railway deployment
            elif platform == "railway":
                # Check if railway CLI is installed
                result = subprocess.run(["which", "railway"], capture_output=True)
                if result.returncode != 0:
                    if console:
                        console.print("[red]Error:[/red] Railway CLI not found")
                        console.print("Install: npm install -g @railway/cli")
                    else:
                        print("Error: Railway CLI not found")
                    raise typer.Exit(code=1)

                if console:
                    console.print("[blue]Deploying to Railway...[/blue]")

                subprocess.run(["railway", "up"], check=True)

                if console:
                    console.print("[green]✓[/green] Deployed to Railway!")
                    console.print("\nView logs: railway logs")
                else:
                    print("✓ Deployed to Railway!")

            # Render deployment
            elif platform == "render":
                # Check if render CLI is installed
                result = subprocess.run(["which", "render"], capture_output=True)
                if result.returncode != 0:
                    if console:
                        console.print("[red]Error:[/red] Render CLI not found")
                        console.print("Install: https://render.com/docs/cli")
                    else:
                        print("Error: Render CLI not found")
                    raise typer.Exit(code=1)

                if console:
                    console.print("[blue]Deploying to Render...[/blue]")

                subprocess.run(["render", "deploy"], check=True)

                if console:
                    console.print("[green]✓[/green] Deployed to Render!")
                else:
                    print("✓ Deployed to Render!")

            # Fly.io deployment
            elif platform == "fly":
                # Check if flyctl is installed
                result = subprocess.run(["which", "flyctl"], capture_output=True)
                if result.returncode != 0:
                    if console:
                        console.print("[red]Error:[/red] Fly CLI not found")
                        console.print("Install: https://fly.io/docs/hands-on/install-flyctl/")
                    else:
                        print("Error: Fly CLI not found")
                    raise typer.Exit(code=1)

                if console:
                    console.print("[blue]Deploying to Fly.io...[/blue]")

                subprocess.run(["flyctl", "deploy"], check=True)

                if console:
                    console.print("[green]✓[/green] Deployed to Fly.io!")
                    console.print("\nView logs: flyctl logs")
                else:
                    print("✓ Deployed to Fly.io!")

            else:
                if console:
                    console.print(f"[red]Error:[/red] Unknown platform: {platform}")
                    console.print("Supported: docker, railway, render, fly")
                else:
                    print(f"Error: Unknown platform: {platform}")
                raise typer.Exit(code=1)

        except subprocess.CalledProcessError as e:
            if console:
                console.print(f"[red]Deployment failed:[/red] {e}")
            else:
                print(f"Deployment failed: {e}")
            raise typer.Exit(code=1) from e
        except Exception as e:
            if console:
                console.print(f"[red]Error:[/red] {e}")
            else:
                print(f"Error: {e}")
            raise typer.Exit(code=1) from e


def main():
    """Entry point for the CLI."""
    if app is None:
        print("Error: typer is not installed. Install with: pip install typer rich")
        sys.exit(1)

    app()


if __name__ == "__main__":
    main()
