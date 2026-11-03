# PropVal AI — Institutional Production Deployment Guide

## 1. Executive Summary & Deployment Architecture

This document provides complete, reproducible instructions for deploying the **PropVal AI** institutional automated property valuation and credit underwriting platform in a secure, containerized on-premise or private cloud environment.

### 1.1 Deployment Topology

```mermaid
flowchart TD
    Client["Client Browser / HFC Underwriter Workstation"]
    
    subgraph Host["Production Server / Private Cloud VM"]
        subgraph DMZ["Public / DMZ Ingress (Ports 80 / 443)"]
            Proxy["Nginx Reverse Proxy & Static SPA<br/>(Container: propval-frontend)<br/>User: nginx (UID 101, Non-root)"]
        end

        subgraph NetFront["frontend-network (Bridge)"]
            Proxy -->|API Reverse Proxy :8000| Backend
        end

        subgraph Core["Application Layer"]
            Backend["FastAPI Valuation & ML Service<br/>(Container: propval-backend)<br/>User: appuser (UID 10001, Non-root)<br/>- CatBoost / SHAP Inference Engine<br/>- Conformal Uncertainty Service<br/>- Gemini API Advisory Integration"]
        end

        subgraph NetBack["backend-network (Isolated Bridge)"]
            Backend -->|SQLAlchemy / psycopg2 :5432| DB
        end

        subgraph Storage["Isolated Database Layer (Zero Host Exposure)"]
            DB[("PostgreSQL 16 + PostGIS<br/>(Container: propval-postgres)<br/>Volume: postgres_data")]
        end
    end

    ExternalGemini["Google Generative AI (Gemini 2.5 Flash)<br/>Optional Advisory Synthesis"]
    Backend -.->|Outbound HTTPS (443)| ExternalGemini
    
    style DB fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc
    style Backend fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc
    style Proxy fill:#1e293b,stroke:#f59e0b,stroke-width:2px,color:#f8fafc
```

### 1.2 Defense-in-Depth Security Guardrails

- **Zero Root Execution**: Both application containers (`propval-backend` and `propval-frontend`) run as dedicated, unprivileged non-root users (`appuser` UID 10001, `nginx` UID 101).
- **Network Segmentation & Database Isolation**: PostgreSQL is attached exclusively to `backend-network`. It does not publish port 5432 to the host and is completely inaccessible to the frontend or public internet.
- **Fail-Fast Startup Validation**: FastAPI validates all production configuration variables at startup and halts execution if SQLite, weak secrets, or wildcard CORS are detected.
- **Audited External Dependencies**: The healthcheck probe verifies external services (such as Gemini); an unavailable external service is flagged as `degraded` or `unavailable` and is never falsely reported as healthy.
- **PII & Credential Scrubbing**: Real-time logging filters redact passwords, JWT tokens, API keys, connection strings, Aadhaar, and PAN numbers from all output streams.

---

## 2. Prerequisites

### 2.1 Hardware Requirements

| Component | Minimum Specification | Recommended Production Specification |
| :--- | :--- | :--- |
| **CPU Architecture** | x86_64 or ARM64 (AVX support recommended) | 8 Cores / 16 Threads |
| **System Memory (RAM)** | 8 GB RAM | 16 GB - 32 GB RAM (for concurrent SHAP / CatBoost calculations) |
| **Storage** | 20 GB SSD | 100 GB+ High-IOPS NVMe SSD |
| **Operating System** | Ubuntu 22.04 LTS, Debian 12, or RHEL 9 | Ubuntu 24.04 LTS (Kernel 6.8+) |

### 2.2 Software Requirements

1. **Docker Engine**: Version 24.0.0 or higher
2. **Docker Compose**: Version 2.20.0 or higher
3. **OpenSSL**: For TLS certificate generation and key exchange
4. **Git**: For repository version management

---

## 3. Docker Installation Guide

### Ubuntu / Debian Linux

```bash
# 1. Update package index and install certificates
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 2. Add Docker official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Configure Docker APT repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Install Docker Engine and Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Enable and start Docker systemd service
sudo systemctl enable --now docker

# 6. (Optional) Allow non-root user execution
sudo usermod -aG docker $USER
newgrp docker
```

---

## 4. Environment Configuration

### 4.1 Configuration Setup

The deployment is driven by environment variables defined in `.env`.

```bash
# Copy the secure production template
cp .env.example .env
chmod 600 .env
```

### 4.2 Cryptographic Key Generation

Before starting the containers, generate a cryptographically strong 256-bit secret key:

```bash
# Generate high-entropy 64-character hex key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output into `.env` for `JWT_SECRET` and `SECRET_KEY`.

### 4.3 Required Environment Variables Checklist

Ensure the following variables are configured in `.env`:

```ini
# Runtime Profile
ENVIRONMENT=production
DEBUG=false
PROJECT_NAME="PropVal AI Institutional Valuation Backend"
VERSION=0.2.0

# Server Bindings
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=https://propval.hero.internal
BACKEND_URL=https://propval.hero.internal/api

# Database Isolation & Credentials
POSTGRES_USER=propval_prod_user
POSTGRES_PASSWORD=Use_A_Strong_Random_Password_Min_20_Chars!
POSTGRES_DB=propval_production
DATABASE_URL=postgresql://propval_prod_user:Use_A_Strong_Random_Password_Min_20_Chars!@db:5432/propval_production

# High-Concurrency Database Pooling
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_PRE_PING=true
DB_POOL_RECYCLE_SECONDS=300

# Authentication & Cryptographic Keys
JWT_SECRET=your_generated_64_char_hex_secret_here
SECRET_KEY=your_generated_64_char_hex_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# CORS Whitelist (Never use '*' in production)
CORS_ORIGINS=https://propval.hero.internal,https://valuation.herohousing.in
BACKEND_CORS_ORIGINS=https://propval.hero.internal,https://valuation.herohousing.in

# In-Memory Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_GLOBAL_PER_MINUTE=120
RATE_LIMIT_AUTH_PER_MINUTE=20

# Gemini AI Advisory Engine (Leave empty for deterministic offline mode)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
ENABLE_AI_CLOUD_PROCESSING=true
```

> [!IMPORTANT]
> The backend startup lifecycle will immediately terminate with an informative error if `ENVIRONMENT=production` and `DATABASE_URL` references SQLite, `SECRET_KEY` is shorter than 32 characters or contains default strings, or `BACKEND_CORS_ORIGINS` contains `*`.

---

## 5. Database Initialization & Migration Execution

Database migrations are executed via **Alembic**. The `propval-backend` container's `docker/entrypoint.sh` executes migrations automatically on startup after verifying database readiness.

### 5.1 Automatic Migration Execution

When Docker Compose starts, the backend entrypoint script:
1. Loops with a health probe until PostgreSQL accepts connections on port 5432.
2. Runs `alembic upgrade head` to apply all schema versions.
3. Spawns 4 production Uvicorn worker processes.

### 5.2 Manual Migration Execution & Verification

To run or verify migrations manually inside the running backend container:

```bash
# Check current database migration version
docker compose exec backend alembic current

# Run pending migrations to head
docker compose exec backend alembic upgrade head

# Inspect migration history
docker compose exec backend alembic history --verbose
```

---

## 6. Application Startup

### 6.1 Building and Launching Containers

```bash
# Build multi-stage images without cache
docker compose build --no-cache

# Start the stack in background daemon mode
docker compose up -d
```

### 6.2 Verifying Container Health and Status

```bash
# View container status, exposed ports, and healthcheck states
docker compose ps
```

Expected output:
```text
NAME                IMAGE                     COMMAND                  SERVICE    STATUS                    PORTS
propval-backend     proval-ai-backend         "/app/entrypoint.sh"     backend    Up (healthy)              8000/tcp
propval-frontend    proval-ai-frontend        "/docker-entrypoint.…"   frontend   Up (healthy)              0.0.0.0:80->8080/tcp, 0.0.0.0:443->8443/tcp
propval-postgres    postgis/postgis:16-3.4    "docker-entrypoint.s…"   db         Up (healthy)              5432/tcp
```

### 6.3 Checking Logs

```bash
# Tail all container logs
docker compose logs -f

# Tail backend structured JSON logs
docker compose logs -f backend
```

---

## 7. HTTPS & Domain Configuration

### 7.1 Production TLS Architecture

PropVal AI includes native TLS termination readiness via `docker/nginx.ssl.conf`.

```text
[Client HTTPS Request :443] 
           │
           ▼
[Nginx TLS Termination] (Ciphers: ECDHE-ECDSA-AES128-GCM-SHA256, TLS 1.2/1.3)
           │
           ├─► /api/*    ──► [FastAPI Backend :8000 via internal frontend-network]
           └─► /*        ──► [Static React 19 SPA Files]
```

### 7.2 Installing Certificates

1. Create a directory for TLS certificates:
   ```bash
   mkdir -p docker/certs
   chmod 700 docker/certs
   ```

2. Place your valid enterprise certificate (`tls.crt`) and private key (`tls.key`) in `docker/certs/`.

   *(For internal testing / staging only, a self-signed certificate can be generated):*
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout docker/certs/tls.key \
     -out docker/certs/tls.crt \
     -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Hero Housing Finance/CN=propval.hero.internal"
   chmod 600 docker/certs/tls.key
   ```

3. Mount the certificates into the frontend container in `docker-compose.yml`:
   ```yaml
   frontend:
     volumes:
       - ./docker/certs:/etc/nginx/certs:ro
       - ./docker/nginx.ssl.conf:/etc/nginx/nginx.conf:ro
   ```

4. Restart the frontend container:
   ```bash
   docker compose up -d --force-recreate frontend
   ```

---

## 8. Health Checks & Monitoring

The system implements three tiers of health checks matching enterprise orchestrator specifications:

### 8.1 Liveness Probe (`GET /health/live`)

- **URL**: `http://localhost/api/v1/health/live` or direct `http://localhost:8000/health/live`
- **Purpose**: Verifies that the FastAPI process is responsive.
- **Expected Status**: `HTTP 200 OK`
- **Response**:
  ```json
  {
    "status": "alive",
    "service": "PropVal AI Institutional Valuation Backend",
    "timestamp": "2026-11-03T16:15:00.000Z"
  }
  ```

### 8.2 Readiness Probe (`GET /health/ready`)

- **URL**: `http://localhost/api/v1/health/ready` or direct `http://localhost:8000/health/ready`
- **Purpose**: Verifies that critical dependencies (PostgreSQL database, ML model registry, Gemini connectivity) are operational before routing traffic.
- **Expected Status**: `HTTP 200 OK` (or `HTTP 503` if DB connection fails).
- **External Dependency Governance**: If Gemini API is configured but fails/times out, status returns `"degraded"`, never false `"healthy"`.
- **Response**:
  ```json
  {
    "status": "ready",
    "ready": true,
    "database": "connected",
    "latencyMs": 1.25,
    "mlEngine": "gated",
    "geminiIntegration": "mock_fallback",
    "timestamp": "2026-11-03T16:15:00.000Z"
  }
  ```

### 8.3 Deep Diagnostic Status (`GET /health`)

- **URL**: `http://localhost/health` or `http://localhost/api/v1/health`
- **Purpose**: Deep verification of the cryptographic audit chain, database latency, and ML model gating.

---

## 9. Backup & Disaster Recovery Procedures

### 9.1 Database Backup Procedure

Perform cold or hot automated PostgreSQL backups using `pg_dump`:

```bash
# Create timestamped backup directory
BACKUP_DIR="/var/backups/propval"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/propval_db_${TIMESTAMP}.sql.gz"

# Execute compressed database dump via Docker exec
docker compose exec -T db pg_dump -U propval_user propval_db | gzip > "$BACKUP_FILE"

# Generate SHA-256 integrity checksum
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"

echo "Backup created at: $BACKUP_FILE"
cat "${BACKUP_FILE}.sha256"
```

### 9.2 Database Restoration Procedure

To restore from a backup:

```bash
# 1. Verify backup file SHA-256 integrity
sha256sum -c "${BACKUP_FILE}.sha256"

# 2. Drop existing connections and restore database
docker compose exec -T db psql -U propval_user -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'propval_db';"

docker compose exec -T db dropdb -U propval_user --if-exists propval_db
docker compose exec -T db createdb -U propval_user propval_db

# 3. Stream backup into PostgreSQL
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U propval_user -d propval_db

# 4. Verify audit trail integrity following restore
docker compose exec backend python -c "
from app.core.database import SessionLocal
from app.services.audit_service import verify_audit_chain
db = SessionLocal()
report = verify_audit_chain(db)
print(f'Audit Chain Valid: {report.is_valid}, Total Events: {report.total_events}')
"
```

---

## 10. Restart & Maintenance Procedures

### 10.1 Graceful Restart

```bash
# Gracefully stop containers (allows in-flight HTTP requests to finish)
docker compose stop

# Restart services
docker compose start
```

### 10.2 Rolling Zero-Downtime Backend Restart

```bash
# Rebuild backend image
docker compose build backend

# Recreate backend container with updated code
docker compose up -d --no-deps --build backend
```

---

## 11. Troubleshooting Guide

| Symptom | Probable Cause | Diagnostic Command & Resolution |
| :--- | :--- | :--- |
| **Backend fails on startup with `CRITICAL PRODUCTION ENVIRONMENT CONFIGURATION FAILURE`** | Required production environment variable missing or default (e.g. SQLite DB URL, weak `SECRET_KEY`). | Check logs: `docker compose logs backend`. Update `.env` with a 32+ char secret and PostgreSQL URL. |
| **Backend healthcheck reports `unhealthy`** | PostgreSQL is not accepting connections, or credentials in `.env` do not match `POSTGRES_PASSWORD`. | Run: `docker compose exec db pg_isready -U propval_user`. Check `DATABASE_URL` credentials in `.env`. |
| **Nginx reports `502 Bad Gateway`** | Backend container has crashed or has not completed startup migrations. | Run: `docker compose ps backend`. Check logs: `docker compose logs backend`. |
| **Gemini reports `unavailable` / Health status `degraded`** | Invalid `GEMINI_API_KEY`, quota exhaustion, or outbound firewall blocking Google API. | Check outbound network: `curl -I https://generativelanguage.googleapis.com`. Or leave `GEMINI_API_KEY=` blank to run in offline fallback mode. |
| **Frontend static assets fail to load (404 on JS/CSS)** | Nginx cache or permission mismatch. | Confirm frontend build: `npm run build`. Ensure Dockerfile copied files to `/usr/share/nginx/html` with `chown=101:101`. |

