# SRMA Engine

Systematic Review & Meta-Analysis Engine — a monorepo for AI-assisted literature review and statistical synthesis.

## Structure

```
srma-engine/
├── apps/
│   ├── api/            # FastAPI backend (Python 3.11)
│   ├── web/            # Next.js 14 frontend (TypeScript)
│   └── stats-worker/   # Python + R meta-analysis microservice
├── infra/
│   └── docker/         # docker-compose.yml + service configs
├── .env.example
└── .gitignore
```

## Quick Start

```bash
# 1. Copy and edit environment variables
cp .env.example infra/docker/.env

# 2. Start infrastructure services
cd infra/docker
docker compose up -d

# 3. Check container health
docker compose ps
```

## Services

| Service   | URL                        | Notes                    |
|-----------|----------------------------|--------------------------|
| API       | http://localhost:8000      | FastAPI + Swagger UI     |
| Web       | http://localhost:3000      | Next.js frontend         |
| Postgres  | localhost:5432             | Main database            |
| Redis     | localhost:6379             | Queue + cache            |
| MinIO     | http://localhost:9000      | PDF / file storage       |
| MinIO UI  | http://localhost:9001      | MinIO console            |
| Grobid    | http://localhost:8070      | PDF → structured TEI XML |
