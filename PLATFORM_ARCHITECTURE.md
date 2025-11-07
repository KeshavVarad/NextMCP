# NextMCP Cloud - Platform Architecture

**Status:** Planning / Pre-MVP
**Repository:** Private (nextmcp-cloud)
**Last Updated:** 2025-11-07

## Overview

NextMCP Cloud is a Vercel-like deployment platform for NextMCP servers. This document outlines the recommended architecture for building a maintainable, scalable SaaS platform.

## Repository Structure

### Two-Repo Strategy

```
nextmcp/                          (PUBLIC - github.com/KeshavVarad/NextMCP)
└── Open source framework

nextmcp-cloud/                    (PRIVATE - New repository)
└── Commercial platform
```

## Technology Stack

### Backend (Control Plane)

**Framework:** FastAPI
**Language:** Python 3.11+
**Database:** PostgreSQL 15+
**Cache/Queue:** Redis 7+
**Background Jobs:** Celery
**ORM:** SQLAlchemy 2.0
**Migrations:** Alembic

**Why:**
- Python consistency with NextMCP framework
- FastAPI = rapid development + excellent docs
- Type safety with Pydantic
- Easy testing with pytest

### Frontend (Dashboard)

**Framework:** Next.js 14 (App Router)
**Language:** TypeScript 5+
**Styling:** TailwindCSS 3+
**Components:** shadcn/ui
**Data Fetching:** TanStack Query
**Charts:** Recharts
**Hosting:** Vercel

**Why:**
- Best-in-class DX for web dashboards
- Type safety prevents bugs
- shadcn/ui = no dependency bloat
- Vercel hosting is free + excellent performance

### CLI Client

**Framework:** Typer (extends existing `mcp` CLI)
**HTTP Client:** httpx
**Output:** Rich

**Integration:**
```bash
# Extends existing NextMCP CLI
mcp deploy                        # Deploy to NextMCP Cloud
mcp logs <deployment-id>         # Stream logs
mcp rollback <deployment-id>     # Rollback deployment
```

### Infrastructure

**Orchestration:** Kubernetes (AWS EKS or GCP GKE)
**IaC:** Terraform
**Monitoring:** Prometheus + Grafana
**Logging:** Loki or CloudWatch
**CI/CD:** GitHub Actions
**Container Registry:** AWS ECR or GCP Artifact Registry

## Project Structure

```
nextmcp-cloud/
├── README.md
├── docker-compose.yml           # Local development
├── Makefile                     # Common tasks
│
├── platform/                    # Control Plane API (FastAPI)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── deployments.py       # Deployment management
│   │   ├── projects.py          # Project management
│   │   ├── metrics.py           # Metrics aggregation
│   │   ├── logs.py              # Log streaming
│   │   └── teams.py             # Team/user management
│   ├── services/
│   │   ├── kubernetes.py        # K8s orchestration
│   │   ├── docker.py            # Container builds
│   │   ├── github.py            # Git integration
│   │   └── billing.py           # Stripe integration
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── deployment.py
│   │   └── team.py
│   ├── tasks/                   # Celery tasks
│   │   ├── build.py             # Build containers
│   │   ├── deploy.py            # Deploy to K8s
│   │   └── cleanup.py           # Cleanup old deployments
│   ├── core/
│   │   ├── config.py            # Configuration
│   │   ├── security.py          # Security utilities
│   │   └── dependencies.py      # FastAPI dependencies
│   ├── tests/
│   ├── alembic/                 # Database migrations
│   ├── main.py                  # FastAPI app entry
│   └── requirements.txt
│
├── dashboard/                   # Web UI (Next.js)
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   └── signup/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── deployments/
│   │   │   │   ├── projects/
│   │   │   │   ├── metrics/
│   │   │   │   ├── logs/
│   │   │   │   └── settings/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   ├── charts/          # Metrics visualizations
│   │   │   ├── deploy/          # Deployment UI
│   │   │   └── nav/             # Navigation
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   ├── hooks.ts         # Custom hooks
│   │   │   └── utils.ts         # Utilities
│   │   └── types/               # TypeScript types
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
│
├── cli-client/                  # CLI Extension
│   ├── nextmcp_cloud/
│   │   ├── __init__.py
│   │   ├── deploy.py            # Deployment logic
│   │   ├── client.py            # HTTP API client
│   │   ├── config.py            # Config management
│   │   └── commands/
│   │       ├── deploy.py
│   │       ├── logs.py
│   │       └── rollback.py
│   ├── tests/
│   ├── setup.py
│   └── README.md
│
├── infrastructure/              # Infrastructure as Code
│   ├── terraform/
│   │   ├── aws/
│   │   │   ├── eks.tf           # Kubernetes cluster
│   │   │   ├── rds.tf           # PostgreSQL
│   │   │   ├── elasticache.tf   # Redis
│   │   │   └── s3.tf            # Object storage
│   │   └── modules/
│   │       ├── database/
│   │       ├── kubernetes/
│   │       └── monitoring/
│   ├── kubernetes/
│   │   ├── base/                # Base configs
│   │   │   ├── namespace.yaml
│   │   │   └── rbac.yaml
│   │   ├── deployments/         # Service deployments
│   │   │   ├── platform-api.yaml
│   │   │   └── builder.yaml
│   │   └── monitoring/
│   │       ├── prometheus.yaml
│   │       └── grafana.yaml
│   └── docker/
│       ├── builder/             # Container builder service
│       └── proxy/               # Ingress proxy
│
├── shared/                      # Shared code
│   ├── schemas/                 # Pydantic/TS schemas
│   └── constants/               # Shared constants
│
├── scripts/                     # Utility scripts
│   ├── db-migrate.sh
│   ├── seed-dev-data.py
│   └── test-deployment.sh
│
└── docs/                        # Internal documentation
    ├── API.md
    ├── DEPLOYMENT.md
    └── DEVELOPMENT.md
```

## Development Workflow

### Local Development Setup

```bash
# Clone repo
git clone git@github.com:yourorg/nextmcp-cloud.git
cd nextmcp-cloud

# Start all services (PostgreSQL, Redis, API, Dashboard)
make dev

# Run migrations
make migrate

# Run tests
make test
```

### Development Tools

**Code Quality:**
- `black` - Code formatting (Python)
- `ruff` - Linting (Python)
- `mypy` - Type checking (Python)
- `prettier` - Code formatting (TypeScript)
- `eslint` - Linting (TypeScript)

**Testing:**
- `pytest` - Unit/integration tests (Python)
- `jest` - Unit tests (TypeScript)
- `playwright` - E2E tests (Dashboard)

**Makefile Commands:**
```makefile
.PHONY: dev test lint format migrate

dev:
	docker-compose up -d
	cd platform && uvicorn main:app --reload &
	cd dashboard && npm run dev

test:
	cd platform && pytest
	cd dashboard && npm test
	cd cli-client && pytest

lint:
	cd platform && ruff check . && mypy .
	cd dashboard && npm run lint

format:
	cd platform && black . && ruff check --fix .
	cd dashboard && npm run format

migrate:
	cd platform && alembic upgrade head
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CloudFlare CDN                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
    ┌───────▼────────┐         ┌───────▼────────┐
    │   Dashboard    │         │  Platform API  │
    │   (Vercel)     │         │   (AWS EKS)    │
    └────────────────┘         └───────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
            ┌───────▼──────┐  ┌────────▼────────┐  ┌─────▼──────┐
            │ PostgreSQL   │  │  Redis Cache    │  │  S3 Logs   │
            │   (RDS)      │  │ (ElastiCache)   │  │            │
            └──────────────┘  └─────────────────┘  └────────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   Kubernetes        │
                            │   ┌──────────────┐  │
                            │   │ User's MCP   │  │
                            │   │ Servers      │  │
                            │   └──────────────┘  │
                            └─────────────────────┘
```

## API Design

### Authentication

```python
# JWT-based authentication
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
```

### Deployments

```python
# Deployment management
POST   /api/v1/deployments              # Create deployment
GET    /api/v1/deployments              # List deployments
GET    /api/v1/deployments/{id}         # Get deployment
DELETE /api/v1/deployments/{id}         # Delete deployment
POST   /api/v1/deployments/{id}/rollback # Rollback
```

### Metrics

```python
# Metrics aggregation
GET /api/v1/deployments/{id}/metrics    # Get metrics
GET /api/v1/deployments/{id}/logs       # Stream logs (SSE)
```

## Database Schema

### Core Tables

```sql
-- Users and authentication
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- Teams for collaboration
CREATE TABLE teams (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL,  -- hobby, pro, team, enterprise
    created_at TIMESTAMP NOT NULL
);

-- Projects (collections of deployments)
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    team_id UUID REFERENCES teams(id),
    name VARCHAR(255) NOT NULL,
    git_repo VARCHAR(255),
    created_at TIMESTAMP NOT NULL
);

-- Deployments
CREATE TABLE deployments (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    status VARCHAR(50) NOT NULL,  -- building, deploying, active, failed
    commit_sha VARCHAR(40),
    container_image VARCHAR(255),
    url VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Metrics (aggregated from Prometheus)
CREATE TABLE metrics (
    id UUID PRIMARY KEY,
    deployment_id UUID REFERENCES deployments(id),
    metric_name VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    timestamp TIMESTAMP NOT NULL
);
```

## Security Considerations

### Authentication
- JWT tokens with 24h expiry
- Refresh tokens with 30d expiry
- Rate limiting on auth endpoints

### Authorization
- Role-based access control (Owner, Admin, Member, Viewer)
- Team-scoped resources
- API key authentication for CLI

### Infrastructure
- Network policies in Kubernetes
- Pod security policies
- Secrets in AWS Secrets Manager
- TLS everywhere
- Regular security audits

## Monitoring & Observability

### Metrics
- **Platform metrics:** API latency, error rates, DB connections
- **User metrics:** Tool invocations, active deployments, bandwidth

### Logging
- Structured JSON logs
- Centralized log aggregation (Loki or CloudWatch)
- 7-day retention (Pro), 30-day retention (Team)

### Alerts
- High error rates
- Deployment failures
- Resource exhaustion
- Billing anomalies

## Cost Optimization

### Infrastructure
- **Auto-scaling:** Scale deployments based on load
- **Spot instances:** Use for non-critical workloads
- **Resource limits:** CPU/memory limits per tier
- **Cold start:** Suspend inactive deployments

### Efficiency
- **Container caching:** Cache Docker layers
- **Multi-tenancy:** Multiple deployments per node
- **Tiered storage:** S3 Glacier for old logs

## Development Phases

### Phase 1: MVP (3-4 months)
- [ ] Platform API (deployments, auth)
- [ ] Basic dashboard (deployments list, logs)
- [ ] CLI integration (`mcp deploy`)
- [ ] Kubernetes orchestration
- [ ] Basic metrics

### Phase 2: Growth (6-8 months)
- [ ] Git integration (auto-deploy)
- [ ] Preview deployments
- [ ] Team collaboration
- [ ] Custom domains
- [ ] Advanced metrics + alerting

### Phase 3: Enterprise (12+ months)
- [ ] Multi-region
- [ ] Auto-scaling
- [ ] SOC2 compliance
- [ ] Enterprise SSO
- [ ] White-label options

## Success Metrics

### Product Metrics
- Deployments per day
- Time to first deployment
- Active users
- User retention
- NPS score

### Business Metrics
- MRR growth
- Conversion rate (free → paid)
- Churn rate
- Customer acquisition cost

## References

- [Vercel Architecture](https://vercel.com/docs)
- [Railway Architecture](https://docs.railway.app/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
