# Simple Deployment Example

A minimal example showing how to deploy a NextMCP application with health checks and graceful shutdown.

## Features

- ✅ Health check endpoints
- ✅ Readiness checks
- ✅ Graceful shutdown handling
- ✅ Production logging
- ✅ Docker deployment ready

## Quick Start

### 1. Install Dependencies

```bash
pip install nextmcp
```

### 2. Run Locally

```bash
python app.py
```

The server will start on `http://localhost:8000`

### 3. Test Health Checks

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test readiness endpoint
curl http://localhost:8000/health/ready
```

## Docker Deployment

### Generate Docker Files

```bash
mcp init --docker
```

This creates:
- `Dockerfile` - Optimized multi-stage build
- `docker-compose.yml` - Local development setup
- `.dockerignore` - Ignore unnecessary files

### Build and Run

```bash
# Build and start containers
docker compose up --build

# View logs
docker compose logs -f

# Stop containers
docker compose down
```

### Test Deployment

```bash
# Health check
curl http://localhost:8000/health

# Test tools
curl -X POST http://localhost:8000/tools/hello \
  -H "Content-Type: application/json" \
  -d '{"name": "Docker"}'
```

## Production Deployment

> **Note:** Cloud platform deployments (Railway, Render, Fly.io) are currently in **Beta**. These integrations use the platform's CLI tools and require manual verification. Community testing and feedback welcome! [Report issues](https://github.com/KeshavVarad/NextMCP/issues)

### Deploy to Railway (Beta)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
mcp deploy --platform railway
```

### Deploy to Fly.io (Beta)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Deploy
mcp deploy --platform fly
```

### Deploy to Render (Beta)

```bash
# Deploy via Git push or CLI
mcp deploy --platform render
```

## Available Tools

### hello
Say hello to someone.

**Parameters:**
- `name` (optional): Name to greet (default: "World")

**Example:**
```python
result = await client.invoke_tool("hello", {"name": "Alice"})
# {"message": "Hello, Alice!", "status": "success"}
```

### health_check
Get application health status.

**Returns:** Health check result with uptime and status

### readiness_check
Get application readiness status.

**Returns:** Readiness check result indicating if app is ready

## Health Check System

The application includes built-in health checks:

### Liveness Check (Health)
- **Endpoint:** `/health`
- **Purpose:** Is the application running?
- **Use:** Kubernetes liveness probe

### Readiness Check (Ready)
- **Endpoint:** `/health/ready`
- **Purpose:** Is the application ready to serve traffic?
- **Use:** Kubernetes readiness probe

### Custom Health Checks

Add your own health checks:

```python
def check_database():
    # Check database connection
    return db.is_connected()

health.add_readiness_check("database", check_database)
```

## Graceful Shutdown

The application handles SIGTERM and SIGINT signals gracefully:

1. Stops accepting new requests
2. Waits for in-flight requests to complete
3. Runs cleanup handlers
4. Exits with proper status code

### Custom Cleanup

Add cleanup handlers:

```python
def close_database():
    db.close()

shutdown.add_cleanup_handler(close_database)
```

## Production Checklist

- [x] Health checks configured
- [x] Graceful shutdown enabled
- [x] Structured logging
- [x] Docker deployment ready
- [ ] Environment variables configured
- [ ] Secrets management
- [ ] Monitoring/alerting
- [ ] Load testing

## Next Steps

1. **Add Authentication:** See `examples/auth_api_key`
2. **Add Metrics:** See `examples/metrics_example`
3. **Scale Horizontally:** Deploy multiple instances
4. **Add Database:** Use `mcp init --docker --with-database`

## Troubleshooting

### Container Won't Start
- Check logs: `docker compose logs`
- Verify port is available: `lsof -i :8000`
- Check health: `docker compose ps`

### Health Check Fails
- Ensure app is fully started (5-10 seconds)
- Check container logs for errors
- Test locally first: `python app.py`

### Deployment Issues
- Verify platform CLI is installed
- Check credentials/authentication
- Review platform-specific logs

## Learn More

- [NextMCP Documentation](https://github.com/KeshavVarad/NextMCP)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Health Checks](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
