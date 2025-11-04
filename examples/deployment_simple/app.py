"""
Simple Deployment Example - NextMCP with Health Checks

This example demonstrates:
- Basic health check endpoints
- Graceful shutdown
- Production-ready configuration
"""

from nextmcp import NextMCP, setup_logging
from nextmcp.deployment import GracefulShutdown, HealthCheck

# Setup logging
setup_logging(level="INFO")

# Create the application
app = NextMCP(name="simple-deployment", description="Simple deployment example with health checks")

# Setup health check system
health = HealthCheck()


# Add a simple readiness check
def check_app_ready():
    """Check if the application is ready to serve requests."""
    # In a real app, you might check database connections, etc.
    return True


health.add_readiness_check("app_ready", check_app_ready)

# Setup graceful shutdown
shutdown = GracefulShutdown(timeout=30.0)


# Add cleanup handler
def cleanup():
    """Cleanup resources on shutdown."""
    print("Cleaning up resources...")
    # Close database connections, flush logs, etc.


shutdown.add_cleanup_handler(cleanup)
shutdown.register()

# Simple tools


@app.tool(name="hello", description="Say hello")
def hello(name: str = "World") -> dict:
    """
    Say hello to someone.

    Args:
        name: Name to greet

    Returns:
        Greeting message
    """
    return {"message": f"Hello, {name}!", "status": "success"}


@app.tool(name="health_check", description="Get application health status")
def get_health() -> dict:
    """
    Get application health status.

    Returns:
        Health check result
    """
    return health.check_health()


@app.tool(name="readiness_check", description="Get application readiness status")
def get_readiness() -> dict:
    """
    Get application readiness status.

    Returns:
        Readiness check result
    """
    return health.check_readiness()


# Run the server
if __name__ == "__main__":
    print("=" * 60)
    print("Simple Deployment Example")
    print("=" * 60)
    print("Starting server with:")
    print("  - Health check endpoint")
    print("  - Graceful shutdown")
    print("  - Production logging")
    print()
    print("Try these commands:")
    print("  mcp init --docker              # Generate Docker files")
    print("  docker compose up --build      # Deploy with Docker")
    print("=" * 60)
    print()

    app.run(host="0.0.0.0", port=8000)
