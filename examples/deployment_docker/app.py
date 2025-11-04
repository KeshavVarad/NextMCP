"""
Docker Deployment Example - Production-Ready NextMCP with Database

This example demonstrates:
- Complete Docker deployment
- Database integration with health checks
- Metrics and monitoring
- Advanced health checks
- Production configuration
"""

import os
import time

from nextmcp import NextMCP, setup_logging
from nextmcp.deployment import GracefulShutdown, HealthCheck, HealthCheckResult, HealthStatus

# Setup logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

# Create the application
app = NextMCP(
    name="docker-deployment",
    description="Production-ready Docker deployment example with database and metrics",
)

# Enable metrics
app.enable_metrics(
    collect_tool_metrics=True, labels={"environment": os.getenv("ENVIRONMENT", "production")}
)

# Setup health check system
health = HealthCheck()

# Simulated database connection
DATABASE_CONNECTED = False
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/nextmcp")


def connect_database():
    """Simulate database connection."""
    global DATABASE_CONNECTED
    try:
        # In a real app, you would connect to the database here
        print(f"Connecting to database: {DATABASE_URL}")
        time.sleep(0.1)  # Simulate connection time
        DATABASE_CONNECTED = True
        print("✓ Database connected")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        DATABASE_CONNECTED = False


# Connect to database on startup
connect_database()


# Database health check
def check_database():
    """Check database connection."""
    if DATABASE_CONNECTED:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection is healthy",
            details={"url": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "unknown"},
        )
    else:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message="Database connection failed",
        )


health.add_readiness_check("database", check_database)


# Disk space health check
def check_disk_space():
    """Check disk space."""
    import shutil

    try:
        usage = shutil.disk_usage("/")
        percent_used = (usage.used / usage.total) * 100

        if percent_used > 90:
            status = HealthStatus.UNHEALTHY
            message = "Disk space critical"
        elif percent_used > 75:
            status = HealthStatus.DEGRADED
            message = "Disk space low"
        else:
            status = HealthStatus.HEALTHY
            message = "Disk space OK"

        return HealthCheckResult(
            name="disk_space",
            status=status,
            message=message,
            details={
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": round(percent_used, 2),
            },
        )
    except Exception as e:
        return HealthCheckResult(
            name="disk_space",
            status=HealthStatus.UNHEALTHY,
            message=f"Failed to check disk space: {e}",
        )


health.add_liveness_check("disk_space", check_disk_space)

# Setup graceful shutdown
shutdown = GracefulShutdown(timeout=30.0)


# Cleanup handler
def cleanup_database():
    """Close database connections."""
    global DATABASE_CONNECTED
    print("Closing database connections...")
    DATABASE_CONNECTED = False
    print("✓ Database connections closed")


shutdown.add_cleanup_handler(cleanup_database)
shutdown.register()

# Tools


@app.tool(name="get_user", description="Get user information")
def get_user(user_id: int) -> dict:
    """
    Get user information from database.

    Args:
        user_id: User ID to retrieve

    Returns:
        User information
    """
    if not DATABASE_CONNECTED:
        return {"error": "Database not connected", "status": "error"}

    # Simulate database query
    return {
        "user_id": user_id,
        "username": f"user_{user_id}",
        "email": f"user_{user_id}@example.com",
        "status": "active",
    }


@app.tool(name="create_user", description="Create a new user")
def create_user(username: str, email: str) -> dict:
    """
    Create a new user in the database.

    Args:
        username: Username for the new user
        email: Email for the new user

    Returns:
        Created user information
    """
    if not DATABASE_CONNECTED:
        return {"error": "Database not connected", "status": "error"}

    # Simulate database insert
    user_id = hash(username + email) % 10000

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "status": "active",
        "created": True,
    }


@app.tool(name="health", description="Get application health status")
def get_health() -> dict:
    """
    Get application health status including all checks.

    Returns:
        Complete health check result
    """
    return health.check_health()


@app.tool(name="metrics", description="Get application metrics")
def get_metrics() -> dict:
    """
    Get application metrics in JSON format.

    Returns:
        Application metrics
    """
    import json

    return json.loads(app.get_metrics_json())


# Run the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    print("=" * 70)
    print("Docker Deployment Example - Production Ready")
    print("=" * 70)
    print(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Not configured'}")
    print(f"Port: {port}")
    print()
    print("Features:")
    print("  ✓ Health checks (liveness + readiness)")
    print("  ✓ Database integration")
    print("  ✓ Metrics collection")
    print("  ✓ Graceful shutdown")
    print("  ✓ Production logging")
    print()
    print("Endpoints:")
    print(f"  Health:     http://localhost:{port}/health")
    print(f"  Readiness:  http://localhost:{port}/health/ready")
    print(f"  Metrics:    http://localhost:{port}/metrics")
    print()
    print("Deployment:")
    print("  docker compose up --build")
    print("  mcp deploy --platform docker")
    print("=" * 70)
    print()

    app.run(host=host, port=port)
