# Docker Deployment Example

A production-ready example showing complete Docker deployment with database, metrics, and advanced health checks.

## Features

- ✅ **Multi-stage Docker build** - Optimized image size
- ✅ **Database integration** - PostgreSQL with health checks
- ✅ **Metrics collection** - Prometheus-compatible metrics
- ✅ **Advanced health checks** - Liveness and readiness probes
- ✅ **Graceful shutdown** - Clean resource cleanup
- ✅ **Environment configuration** - 12-factor app compliant
- ✅ **Production logging** - Structured JSON logs
- ✅ **Security hardening** - Non-root user, minimal attack surface

## Quick Start

### 1. Generate Docker Files

```bash
cd examples/deployment_docker
mcp init --docker --with-database
```

This generates:
- `Dockerfile` - Optimized multi-stage build
- `docker-compose.yml` - With PostgreSQL included
- `.dockerignore` - Minimal image size

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Build and Run

```bash
docker compose up --build
```

The application will be available at `http://localhost:8000`

### 4. Test the Deployment

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Metrics
curl http://localhost:8000/metrics

# Create a user
curl -X POST http://localhost:8000/tools/create_user \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com"}'

# Get user
curl -X POST http://localhost:8000/tools/get_user \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1234}'
```

## Architecture

```
┌─────────────────────────────────────────┐
│        Docker Compose Stack             │
├─────────────────────────────────────────┤
│                                         │
│  ┌────────────────┐  ┌──────────────┐  │
│  │  NextMCP App   │──│  PostgreSQL  │  │
│  │                │  │              │  │
│  │  Port: 8000    │  │  Port: 5432  │  │
│  │  Health: ✓     │  │  Volume: ✓   │  │
│  └────────────────┘  └──────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

## Docker Configuration

### Dockerfile

The multi-stage Dockerfile:
1. **Builder stage**: Installs dependencies
2. **Runtime stage**: Minimal production image

```dockerfile
# Stage 1: Builder
FROM python:3.10-slim as builder
# Install dependencies...

# Stage 2: Runtime
FROM python:3.10-slim
# Copy only what's needed
# Run as non-root user
```

### docker-compose.yml

```yaml
services:
  nextmcp-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; ..."]
      interval: 30s

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=nextmcp
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

## Health Checks

The application implements comprehensive health checks:

### Liveness Checks
These determine if the container should be restarted:

#### Disk Space Check
```json
{
  "name": "disk_space",
  "status": "healthy",
  "details": {
    "total_gb": 100.0,
    "used_gb": 45.2,
    "free_gb": 54.8,
    "percent_used": 45.2
  }
}
```

### Readiness Checks
These determine if the container should receive traffic:

#### Database Check
```json
{
  "name": "database",
  "status": "healthy",
  "message": "Database connection is healthy",
  "details": {
    "url": "postgres:5432"
  }
}
```

### Using Health Checks

In Kubernetes:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Metrics

The application exposes Prometheus-compatible metrics:

```bash
# View metrics
curl http://localhost:8000/metrics
```

Metrics include:
- Tool invocation counts
- Tool execution durations
- Success/error rates
- Custom application metrics

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'nextmcp'
    static_configs:
      - targets: ['nextmcp-app:8000']
    metrics_path: '/metrics'
```

## Production Deployment

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Application port | `8000` |
| `HOST` | Bind address | `0.0.0.0` |
| `ENVIRONMENT` | Environment name | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | Required |

### Security

The application follows security best practices:

1. **Non-root user**: Runs as user `nextmcp` (UID 1000)
2. **Minimal base image**: Python slim variant
3. **No unnecessary packages**: Only production dependencies
4. **Read-only filesystem compatible**: State in volumes
5. **Health checks**: Automatic restart on failure

### Scaling

#### Horizontal Scaling

```bash
# Scale to 3 replicas
docker compose up --scale nextmcp-app=3 -d
```

#### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nextmcp
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: nextmcp
        image: nextmcp:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Monitoring

### View Logs

```bash
# All logs
docker compose logs -f

# App logs only
docker compose logs -f nextmcp-app

# Database logs
docker compose logs -f postgres
```

### Container Status

```bash
# View running containers
docker compose ps

# View resource usage
docker stats

# Inspect container
docker inspect nextmcp-app
```

### Database

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d nextmcp

# View database logs
docker compose logs postgres
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker compose logs nextmcp-app

# Verify configuration
docker compose config

# Check port conflicts
lsof -i :8000
```

### Database Connection Failed

```bash
# Check database is running
docker compose ps postgres

# Test database connection
docker compose exec postgres pg_isready

# View database logs
docker compose logs postgres
```

### Health Check Failing

```bash
# Manual health check
curl http://localhost:8000/health

# Check container health
docker inspect nextmcp-app | grep Health -A 10

# View detailed logs
docker compose logs -f --tail=100
```

### Performance Issues

```bash
# Check resource usage
docker stats

# View metrics
curl http://localhost:8000/metrics | grep duration

# Increase resources in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

## Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] SSL/TLS certificates configured
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting setup
- [ ] Log aggregation configured
- [ ] Resource limits set
- [ ] Security scanning completed
- [ ] Load testing performed
- [ ] Disaster recovery plan documented

## Advanced Topics

### Multi-Stage Builds

Optimize image size:
```dockerfile
# Development stage (not shipped)
FROM python:3.10 as dev
RUN pip install pytest black ruff
# ...

# Production stage (shipped)
FROM python:3.10-slim
COPY --from=builder /dependencies /
# ...
```

### Secrets Management

Use Docker secrets or environment variables:
```yaml
services:
  nextmcp-app:
    secrets:
      - database_password
secrets:
  database_password:
    external: true
```

### Volume Mounts

For development:
```yaml
services:
  nextmcp-app:
    volumes:
      - ./app.py:/app/app.py  # Hot reload
      - ./data:/app/data      # Persistent data
```

## Learn More

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [12-Factor App](https://12factor.net/)
- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)
