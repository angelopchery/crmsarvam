# Runtime Fixes - Complete Summary

## ISSUES FIXED

### Issue 1: Database Does Not Exist
**Error:** `FATAL: database "crm_user" does not exist`

**Root Cause:** Database credentials were inconsistent and potentially confusing. The old setup used:
- PostgreSQL user: `crm_user`
- PostgreSQL database: `crmsarvam`

This could cause confusion in connection strings.

**Fix:** Standardized to simple, memorable credentials:
- PostgreSQL user: `postgres`
- PostgreSQL password: `postgres`
- PostgreSQL database: `crmsarvam`

**Files Modified:**
- `docker-compose.yml` - Updated PostgreSQL environment variables
- `.env` - Updated DATABASE_URL for local development
- `app/core/config.py` - Updated default DATABASE_URL
- `.env.example` - Updated for consistency

---

### Issue 2: Port 8000 Already in Use
**Error:** `Bind for 0.0.0.0:8000 failed`

**Root Cause:** Port 8000 was being used by another process/container.

**Fix:** Changed backend port mapping from `8000:8000` to `8001:8000`

**Files Modified:**
- `docker-compose.yml` - Changed backend port mapping to `"8001:8000"`
- `frontend/vite.config.js` - Updated proxy target to `http://localhost:8001`

**Note:** `nginx.conf` continues to proxy to `http://backend:8000` which is correct because it uses the internal port within the Docker network.

---

## DATABASE CONFIGURATION (FINAL)

### Docker Environment (docker-compose.yml)
```yaml
postgres:
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: crmsarvam

backend:
  environment:
    DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/crmsarvam

celery-worker:
  environment:
    DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/crmsarvam
```

### Local Development (.env)
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/crmsarvam
```

### Default (config.py)
```python
DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/crmsarvam"
```

---

## PORT CONFIGURATION (FINAL)

### Docker Compose Port Mappings

| Service | Host Port | Container Port | Access URL |
|---------|-----------|----------------|------------|
| Frontend | 3000 | 80 | http://localhost:3000 |
| Backend | 8001 | 8000 | http://localhost:8001 |
| PostgreSQL | 5432 | 5432 | postgresql://localhost:5432 |
| Redis | 6379 | 6379 | redis://localhost:6379 |

### Internal Service Communication

| Service | Connects To | URL |
|---------|--------------|-----|
| Frontend (nginx) | Backend | `http://backend:8000` |
| Backend | PostgreSQL | `postgresql://postgres:5432/crmsarvam` |
| Backend | Redis | `redis://redis:6379/0` |
| Celery Worker | PostgreSQL | `postgresql://postgres:5432/crmsarvam` |
| Celery Worker | Redis | `redis://redis:6379/0` |

### Local Development Proxy (vite.config.js)
```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8001',  // Backend on port 8001
  },
  '/uploads': {
    target: 'http://localhost:8001',
  },
}
```

---

## DEPENDENCY ORDER IMPROVEMENTS

### Enhanced Health Checks

**PostgreSQL:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Backend:**
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
  interval: 30s
  timeout: 10s
  start_period: 40s
  retries: 3
```

**Redis:**
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### Service Dependencies

**Backend depends on:**
- PostgreSQL (with health check)
- Redis (with health check)

**Celery Worker depends on:**
- PostgreSQL (with health check)
- Redis (with health check)
- Backend (with health check) - ensures backend is fully initialized

**Frontend depends on:**
- Backend (with health check) - ensures API is available

---

## FILES MODIFIED

1. **docker-compose.yml**
   - Changed PostgreSQL credentials to `postgres/postgres`
   - Changed backend port mapping to `8001:8000`
   - Added backend health check
   - Enhanced dependency conditions
   - Improved startup command with better logging

2. **.env**
   - Updated DATABASE_URL for local development
   - Added comment about Docker override

3. **app/core/config.py**
   - Updated default DATABASE_URL to use new credentials
   - Added comment about Docker override

4. **frontend/vite.config.js**
   - Updated proxy target to port 8001

5. **.env.example**
   - Updated to reflect new database configuration
   - Added comments about Docker vs local development

6. **frontend/nginx.conf**
   - No changes needed (proxies to correct internal port 8000)

---

## DATABASE INITIALIZATION

The system uses Alembic for database migrations. The backend startup command includes:
```bash
alembic upgrade head
```

This automatically runs when the backend starts, creating all necessary tables.

---

## STARTUP COMMANDS

### Clean Start (First Time)
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Prune all build cache
docker builder prune -a -f

# Build and start
docker-compose build --no-cache
docker-compose up -d

# View logs
docker-compose logs -f
```

### Standard Start
```bash
docker-compose up -d
```

### Rebuild and Start
```bash
docker-compose up -d --build
```

### View Specific Service Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# PostgreSQL only
docker-compose logs -f postgres

# Celery worker only
docker-compose logs -f celery-worker
```

---

## SERVICE HEALTH CHECKS

### Backend Health Check
```bash
# From host
curl http://localhost:8001/health

# Expected output:
# {"status":"healthy"}

# API health check
curl http://localhost:8001/api/health
```

### Frontend Health Check
```bash
curl http://localhost:3000

# Should return HTML from React app
```

### PostgreSQL Health Check
```bash
docker-compose exec postgres pg_isready -U postgres

# Expected: accepting connections
```

### Redis Health Check
```bash
docker-compose exec redis redis-cli ping

# Expected: PONG
```

---

## TROUBLESHOOTING

### Issue: "database does not exist"
**Solution:**
```bash
# Check PostgreSQL container logs
docker-compose logs postgres

# Verify database exists
docker-compose exec postgres psql -U postgres -d crmsarvam -c "\l"

# If missing, recreate database
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE crmsarvam;"
```

### Issue: "Connection refused" to backend
**Solutions:**
1. Verify backend is running:
   ```bash
   docker-compose ps backend
   ```

2. Check backend logs:
   ```bash
   docker-compose logs backend
   ```

3. Verify health check:
   ```bash
   docker-compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
   ```

### Issue: Port already in use
**Solution:**
```bash
# Check what's using port 8001
netstat -ano | findstr :8001

# Or use lsof on Linux/Mac
lsof -i :8001

# Change port in docker-compose.yml if needed
```

### Issue: Celery worker fails to start
**Solutions:**
1. Check Celery worker logs:
   ```bash
   docker-compose logs celery-worker
   ```

2. Verify Redis is accessible:
   ```bash
   docker-compose exec celery-worker celery -A app.workers.celery_app inspect active
   ```

3. Restart Celery worker:
   ```bash
   docker-compose restart celery-worker
   ```

---

## LOCAL DEVELOPMENT SETUP

If you want to run the backend locally (without Docker):

### 1. Install Dependencies
```bash
# Python
pip install -r requirements.txt

# PostgreSQL
# Install PostgreSQL 14+ and create database:
# createdb crmsarvam
```

### 2. Configure Environment
```bash
# .env file
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/crmsarvam
REDIS_URL=redis://localhost:6379/0
```

### 3. Run Migrations
```bash
alembic upgrade head
```

### 4. Create Admin User
```bash
python scripts/create_admin.py --username admin --password admin123
```

### 5. Start Services
```bash
# Terminal 1: Backend
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Celery Worker
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Frontend
cd frontend
npm install
npm run dev
```

---

## PRODUCTION DEPLOYMENT NOTES

1. **Stronger Credentials**
   ```bash
   # Generate strong passwords
   openssl rand -hex 32  # For SECRET_KEY
   openssl rand -hex 16  # For DB password
   ```

2. **Database Backups**
   ```bash
   # Backup
   docker-compose exec postgres pg_dump -U postgres crmsarvam > backup.sql

   # Restore
   docker-compose exec -T postgres psql -U postgres crmsarvam < backup.sql
   ```

3. **Persistent Redis**
   ```yaml
   # Add to redis service in docker-compose.yml
   command: redis-server --appendonly yes
   ```

4. **Resource Limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 1G
       reservations:
         cpus: '0.5'
         memory: 512M
   ```

5. **SSL/TLS**
   Use reverse proxy (nginx/traefik) with HTTPS

---

## VERIFICATION CHECKLIST

- [x] Database credentials standardized (postgres/postgres/crmsarvam)
- [x] Backend port changed to 8001
- [x] nginx.conf proxies to correct internal port (8000)
- [x] vite.config.js proxies to port 8001
- [x] .env updated for consistency
- [x] .env.example updated
- [x] config.py default updated
- [x] Health checks configured for all services
- [x] Dependency order enhanced
- [x] Startup command improved with logging

---

## SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                         │
└─────────────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    ↓         │
┌──────────┐ │    ┌──────────────┐    ┌──────────┐
│ Frontend │ │    │   Backend    │    │  Redis   │
│  :3000   │ │    │   :8001      │    │  :6379   │
│  (nginx) │─┼────►  (gunicorn)   ├────►           │
└──────────┘ │    └──────┬───────┘    └──────────┘
             │           │
             │           ↓
             │    ┌──────────────┐
             │    │  PostgreSQL  │
             │    │    :5432     │
             │    │  crmsarvam   │
             │    └──────────────┘
             │
             │    ┌──────────────┐
             └────► Celery Worker│
                  │  + FFmpeg    │
                  └──────────────┘
```

---

## EXPECTED STARTUP LOGS

### PostgreSQL
```
crmsarvam-postgres | The files belonging to this database system will be owned by user "postgres".
crmsarvam-postgres | initdb: warning: enabling "trust" authentication for local connections
crmsarvam-postgres | database system is ready to accept connections
crmsarvam-postgres | starting PostgreSQL 15.x
```

### Backend
```
crmsarvam-backend | Waiting for database...
crmsarvam-backend | Running database migrations...
crmsarvam-backend | INFO  [alembic.env] Migration context: Postgresql
crmsarvam-backend | INFO  [alembic.env] Will assume non-transactional DDL.
crmsarvam-backend | Running upgrade ->
crmsarvam-backend | Starting server...
crmsarvam-backend | [INFO] Starting gunicorn
```

### Celery Worker
```
crmsarvam-celery-worker |
crmsarvam-celery-worker |  * Starting worker...
crmsarvam-celery-worker |  * Connected to redis://redis:6379/0
crmsarvam-celery-worker |  * celery@xxxxx ready.
```

### Frontend
```
crmsarvam-frontend | /docker-entrypoint.sh: /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh: info: IPv6 addresses are not preferred.
crmsarvam-frontend | /docker-entrypoint.sh: Launching /docker-entrypoint.d/50-healthcheck.sh
crmsarvam-frontend | /docker-entrypoint.sh: Launching nginx...
```

---

## CONCLUSION

All runtime issues have been resolved:
1. ✅ Database credentials standardized
2. ✅ Port conflict resolved (8000 → 8001)
3. ✅ Health checks configured
4. ✅ Dependency order enhanced
5. ✅ All configurations aligned

The system should now start successfully with `docker-compose up -d`.
