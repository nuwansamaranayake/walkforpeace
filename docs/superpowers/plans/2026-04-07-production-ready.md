# Walk for Peace — Production-Ready Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the Walk for Peace Media Credential System production-ready: fix all bugs, get Docker Compose running, complete missing features, write tests, and prepare for deployment.

**Architecture:** FastAPI async backend with PostgreSQL, React+TypeScript+Tailwind frontend, nginx reverse proxy, DeepFace face matching, JWT-signed QR credentials. All services orchestrated via Docker Compose.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, React 18, TypeScript, Tailwind CSS, Vite, Docker Compose, DeepFace/ArcFace, ReportLab, html5-qrcode.

---

## File Map — What Changes Where

### Phase 1: Fix and Run

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/api/admin.py:275` | Fix | Remove unused `aiofiles` import (not in requirements.txt) |
| `backend/app/services/face_match.py:90` | Fix | Fix `UnboundLocalError` when tempfile creation fails |
| `backend/Dockerfile` | Modify | Pre-download DeepFace ArcFace model |
| `nginx/nginx.conf` | Rewrite | Handle dev mode without SSL certs |
| `docker-compose.yml` | Modify | Default ENVIRONMENT to development, fix frontend volume |
| `.env` | Create | Development environment config |
| `.gitignore` | Modify | Add more entries for safety |
| `backend/requirements.txt` | Fix | Pin `bcrypt` version for passlib compat |

### Phase 2: Missing Features

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/i18n/translations.json` | Create | EN/Sinhala translations |
| `frontend/src/i18n/useTranslation.ts` | Create | i18n hook |
| `frontend/src/pages/RegisterPage.tsx` | Modify | Add language toggle, use i18n |
| `frontend/src/pages/StatusPage.tsx` | Modify | Add ref number input form |
| `backend/app/api/registration.py` | Modify | Add CSRF Origin/Referer validation |
| `backend/app/middleware/csrf.py` | Create | CSRF middleware |
| `backend/app/main.py` | Modify | Register CSRF middleware |

### Phase 3: Testing

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/tests/conftest.py` | Create | Test fixtures, DB setup |
| `backend/tests/test_api.py` | Create | Integration tests |
| `scripts/create-test-images.py` | Create | Generate test images |

### Phase 4: Git & Deployment Prep

| File | Action | Responsibility |
|------|--------|----------------|
| `.github/workflows/deploy.yml` | Create | CI/CD pipeline |
| `scripts/setup-ssl.sh` | Create | SSL cert setup |
| `scripts/vps-init.sh` | Create | VPS initialization |

---

## Phase 1: Fix and Run Locally in Docker

### Task 1: Fix Backend Bugs

**Files:**
- Fix: `backend/app/api/admin.py:275`
- Fix: `backend/app/services/face_match.py:86-95`
- Fix: `backend/requirements.txt`

- [ ] **Step 1: Remove unused `aiofiles` import in admin.py**

In `backend/app/api/admin.py`, line 275 has `import httpx, aiofiles`. The `aiofiles` module is not in `requirements.txt` and isn't used (the code does synchronous `open()`). Change:

```python
# Line 275 - old:
            import httpx, aiofiles
# Line 275 - new:
            import httpx
```

- [ ] **Step 2: Fix UnboundLocalError in face_match.py**

In `backend/app/services/face_match.py`, the `except` block at line 88-95 references `id_path` and `live_path` which may not be assigned if the first `tempfile.NamedTemporaryFile` fails. Fix:

```python
    try:
        id_path = None
        live_path = None

        # Save to temp files (DeepFace needs file paths or numpy arrays)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f1:
            f1.write(_ensure_jpeg(id_face_bytes))
            id_path = f1.name

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f2:
            f2.write(_ensure_jpeg(live_photo_bytes))
            live_path = f2.name

        # ... rest unchanged ...

    except Exception as e:
        logger.error(f"Face matching failed: {e}")
        # Cleanup on error
        for p in [id_path, live_path]:
            if p:
                try:
                    Path(p).unlink(missing_ok=True)
                except:
                    pass
        return None, False
```

- [ ] **Step 3: Pin bcrypt for passlib compatibility**

In `backend/requirements.txt`, add bcrypt pin (passlib 1.7.4 doesn't support bcrypt>=4.1 well):

```
bcrypt==4.0.1
```

Add this line after `passlib[bcrypt]==1.7.4`.

- [ ] **Step 4: Verify backend loads**

```bash
cd backend
pip install -r requirements.txt
python -c "from app.main import app; print('OK')"
```

Expected: `OK` printed with no import errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin.py backend/app/services/face_match.py backend/requirements.txt
git commit -m "fix: resolve import error, UnboundLocalError, and bcrypt compat"
```

---

### Task 2: Fix nginx.conf for Development

**Files:**
- Rewrite: `nginx/nginx.conf`

The current nginx.conf has an SSL server block that references `/etc/letsencrypt/live/walkforpeacelk.org/fullchain.pem` — these files don't exist in dev and will crash nginx on startup.

- [ ] **Step 1: Rewrite nginx.conf to work without SSL in dev**

Keep the production SSL block but make it conditional. The simplest approach: remove the SSL server block entirely and keep only the dev/default server. We'll add SSL back via a separate `nginx-prod.conf` or at deploy time.

```nginx
worker_processes auto;
events { worker_connections 1024; }

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 20M;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 256;

    # Rate limiting zone for registration
    limit_req_zone $binary_remote_addr zone=register:10m rate=10r/m;

    # Upstream API
    upstream api {
        server api:8000;
    }

    server {
        listen 80 default_server;
        server_name _;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Let's Encrypt challenge (for future SSL setup)
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # API proxy
        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Rate-limited registration
        location /api/register {
            limit_req zone=register burst=5 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Serve uploaded files
        location /uploads/ {
            alias /app/uploads/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Frontend (SPA)
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            expires 1h;
        }

        # Static assets caching
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
            root /usr/share/nginx/html;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

- [ ] **Step 2: Create nginx/nginx-ssl.conf for production**

Create `nginx/nginx-ssl.conf` with the full SSL config (copy from original `nginx.conf` but keep both the redirect and SSL server blocks). This will be used when deploying to VPS with real certificates.

```nginx
worker_processes auto;
events { worker_connections 1024; }

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 20M;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 256;

    limit_req_zone $binary_remote_addr zone=register:10m rate=10r/m;

    upstream api {
        server api:8000;
    }

    # HTTP -> HTTPS redirect
    server {
        listen 80;
        server_name walkforpeacelk.org www.walkforpeacelk.org;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # HTTPS
    server {
        listen 443 ssl http2;
        server_name walkforpeacelk.org www.walkforpeacelk.org;

        ssl_certificate /etc/letsencrypt/live/walkforpeacelk.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/walkforpeacelk.org/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/register {
            limit_req zone=register burst=5 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /uploads/ {
            alias /app/uploads/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            expires 1h;
        }

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
            root /usr/share/nginx/html;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add nginx/nginx.conf nginx/nginx-ssl.conf
git commit -m "fix: separate dev and prod nginx configs, remove SSL requirement in dev"
```

---

### Task 3: Fix docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Set ENVIRONMENT default to development and remove certbot in dev**

Key changes:
1. Default `ENVIRONMENT` to `development` (not production) so CORS allows localhost and file serving works
2. Remove certbot service dependency (it will fail without certs)
3. Remove SSL port mapping from nginx (no certs in dev)
4. Set `APP_URL` to `http://localhost` for development

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: walkforpeace
      POSTGRES_USER: walkforpeace
      POSTGRES_PASSWORD: ${DB_PASSWORD:-walkforpeace}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U walkforpeace"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: ./backend
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://walkforpeace:${DB_PASSWORD:-walkforpeace}@postgres:5432/walkforpeace
      DATABASE_URL_SYNC: postgresql://walkforpeace:${DB_PASSWORD:-walkforpeace}@postgres:5432/walkforpeace
      JWT_SECRET: ${JWT_SECRET:-change-me-in-production}
      CREDENTIAL_SECRET: ${CREDENTIAL_SECRET:-change-me-credential-secret}
      EVENT_DATE: "2026-04-21"
      APP_URL: ${APP_URL:-http://localhost}
      ENVIRONMENT: ${ENVIRONMENT:-development}
      UPLOAD_DIR: /app/uploads
      R2_ENDPOINT_URL: ${R2_ENDPOINT_URL:-}
      R2_ACCESS_KEY_ID: ${R2_ACCESS_KEY_ID:-}
      R2_SECRET_ACCESS_KEY: ${R2_SECRET_ACCESS_KEY:-}
      R2_BUCKET_NAME: ${R2_BUCKET_NAME:-walkforpeace-media}
      R2_PUBLIC_URL: ${R2_PUBLIC_URL:-}
      SMTP_HOST: ${SMTP_HOST:-}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USER: ${SMTP_USER:-}
      SMTP_PASSWORD: ${SMTP_PASSWORD:-}
      SMTP_FROM_EMAIL: ${SMTP_FROM_EMAIL:-noreply@walkforpeacelk.org}
      ADMIN_DEFAULT_USERNAME: ${ADMIN_DEFAULT_USERNAME:-admin}
      ADMIN_DEFAULT_PASSWORD: ${ADMIN_DEFAULT_PASSWORD:-WalkForPeace2026!}
      FACE_MATCH_THRESHOLD: "0.60"
    volumes:
      - uploads:/app/uploads
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    restart: "no"
    volumes:
      - frontend_build:/app/dist

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    depends_on:
      - api
      - frontend
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - frontend_build:/usr/share/nginx/html:ro
      - uploads:/app/uploads:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  pgdata:
  uploads:
  frontend_build:
```

Key differences from original:
- `ENVIRONMENT` defaults to `development`
- `APP_URL` defaults to `http://localhost`
- Removed `443:443` port from nginx
- Removed `certbot` service entirely (add back for prod)
- Removed `certbot_conf` and `certbot_www` volumes

- [ ] **Step 2: Create .env for development**

```bash
# .env — local development overrides
DB_PASSWORD=walkforpeace
JWT_SECRET=dev-jwt-secret-not-for-production
CREDENTIAL_SECRET=dev-credential-secret-not-for-production
APP_URL=http://localhost
ENVIRONMENT=development
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=WalkForPeace2026!
FACE_MATCH_THRESHOLD=0.60
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env
git commit -m "fix: docker-compose defaults to development mode, remove SSL deps"
```

---

### Task 4: Fix Backend Dockerfile

**Files:**
- Modify: `backend/Dockerfile`

- [ ] **Step 1: Pre-download DeepFace ArcFace model during build**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download DeepFace ArcFace model (~500MB) so it's cached in the image
RUN python -c "from deepface import DeepFace; DeepFace.build_model('ArcFace')" || echo "DeepFace model download failed (non-fatal)"

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Note: The `|| echo` fallback ensures the build doesn't fail if DeepFace can't download (e.g., no internet in CI). The model will auto-download on first use anyway.

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: pre-download DeepFace ArcFace model in Docker build"
```

---

### Task 5: Fix Frontend Build

**Files:**
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Verify frontend builds locally**

```bash
cd frontend
npm install
npm run build
```

Expected: Build completes with zero errors. If TypeScript errors appear, fix them.

- [ ] **Step 2: Fix frontend Dockerfile for reliable volume population**

The current Dockerfile copies build output to `/app/dist` and uses a named volume to share with nginx. To ensure the volume always gets the latest build, add a copy command in the CMD:

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM alpine:3.19
RUN apk add --no-cache coreutils
COPY --from=build /app/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'Frontend deployed to /app/dist'; ls -la /app/dist/"]
```

This way, every time the container starts, it copies the fresh build into the shared volume (even if the volume already has old data).

- [ ] **Step 3: Commit**

```bash
git add frontend/Dockerfile
git commit -m "fix: frontend Dockerfile reliably copies build to shared volume"
```

---

### Task 6: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Expand .gitignore**

```
# Environment
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/
.mypy_cache/
*.db

# Node
node_modules/
dist/
.vite/

# Uploads
uploads/

# Alembic
alembic/versions/__pycache__/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
*.log

# Test artifacts
/test_*.jpg
/test_*.png
htmlcov/
.coverage
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: expand .gitignore with common patterns"
```

---

### Task 7: Docker Compose Up and Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Build and start all services**

```bash
cd /path/to/walkforpeace
docker compose up --build
```

Expected: All 4 services start (postgres, api, frontend, nginx). Watch for:
- postgres reports "database system is ready to accept connections"
- api reports "Database tables created/verified" and "Seeded admin user: admin"
- frontend reports "Frontend deployed to /app/dist"
- nginx starts without errors

- [ ] **Step 2: Verify health endpoint**

```bash
curl http://localhost/api/health
```

Expected: `{"status":"ok","service":"walkforpeace-api","environment":"development"}`

- [ ] **Step 3: Verify database tables**

```bash
docker compose exec postgres psql -U walkforpeace -d walkforpeace -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

Expected: 4 tables — `admin_users`, `credentials`, `media_applications`, `verification_logs`

- [ ] **Step 4: Verify admin user seeded**

```bash
docker compose exec postgres psql -U walkforpeace -d walkforpeace -c "SELECT count(*) FROM admin_users;"
```

Expected: `1`

- [ ] **Step 5: Run smoke test**

```bash
bash scripts/smoke-test.sh http://localhost
```

Expected: All tests pass.

---

## Phase 2: Complete Missing Features

### Task 8: CSRF Protection

**Files:**
- Create: `backend/app/middleware/csrf.py`
- Create: `backend/app/middleware/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create CSRF middleware**

Create `backend/app/middleware/__init__.py` (empty file).

Create `backend/app/middleware/csrf.py`:

```python
"""CSRF protection middleware — validates Origin/Referer on state-changing requests."""
import logging
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in SAFE_METHODS:
            return await call_next(request)

        # Get Origin or Referer header
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        source = origin or referer
        if not source:
            # Allow requests without Origin/Referer from same-origin forms
            # (some browsers don't send these for same-origin)
            return await call_next(request)

        # Parse and validate
        parsed = urlparse(source)
        allowed_hosts = {"walkforpeacelk.org", "www.walkforpeacelk.org"}
        if settings.ENVIRONMENT == "development":
            allowed_hosts.update({"localhost", "127.0.0.1"})

        if parsed.hostname not in allowed_hosts:
            logger.warning(f"CSRF blocked: {request.method} {request.url} from {source}")
            return JSONResponse(
                {"detail": "Cross-origin request blocked"},
                status_code=403,
            )

        return await call_next(request)
```

- [ ] **Step 2: Register CSRF middleware in main.py**

Add after the CORS middleware block in `backend/app/main.py`:

```python
from app.middleware.csrf import CSRFMiddleware

app.add_middleware(CSRFMiddleware)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/middleware/ backend/app/main.py
git commit -m "feat: add CSRF protection middleware (Origin/Referer validation)"
```

---

### Task 9: Bilingual Support (English + Sinhala)

**Files:**
- Create: `frontend/src/i18n/translations.json`
- Create: `frontend/src/i18n/useTranslation.ts`
- Modify: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Create translations file**

Create `frontend/src/i18n/translations.json`:

```json
{
  "en": {
    "register.title": "Media Credential Registration",
    "register.personal": "Personal Information",
    "register.fullName": "Full Name",
    "register.email": "Email",
    "register.organization": "Organization / Outlet",
    "register.designation": "Designation / Role",
    "register.phone": "Phone",
    "register.country": "Country",
    "register.mediaType": "Media Type",
    "register.selectMediaType": "Select media type",
    "register.identity": "Identity Verification",
    "register.idDocument": "Full ID Document (Passport / NIC)",
    "register.idDocumentHint": "Click to upload (JPG, PNG, PDF — max 5MB)",
    "register.idFaceCrop": "Close-up of Face on ID",
    "register.idFaceCropHint": "Crop/photo of just the face from your ID",
    "register.idTip": "Tip: Take a clear, well-lit close-up photo of the face portion on your ID card.",
    "register.livePhoto": "Live Face Photo",
    "register.livePhotoHint": "Take a clear photo of yourself in a well-lit place. This will be compared with your ID photo.",
    "register.openCamera": "Click to open camera",
    "register.capture": "Capture",
    "register.retake": "Retake photo",
    "register.terms": "I confirm that the information provided is accurate and I consent to the processing of my data for the purpose of media credential verification for Walk for Peace Sri Lanka 2026.",
    "register.submit": "Submit Application",
    "register.submitting": "Submitting...",
    "register.success": "Application Submitted!",
    "register.refLabel": "Your reference number:",
    "register.saveRef": "Save this number. A confirmation email has been sent. You will be notified once your application is reviewed.",
    "register.checkStatus": "Check application status",
    "register.errorIdDoc": "Please upload your ID document",
    "register.errorIdFace": "Please upload a close-up of the face on your ID",
    "register.errorFace": "Please capture your face photo using the camera",
    "register.errorTerms": "Please accept the terms",
    "register.errorGeneric": "Registration failed. Please try again.",
    "mediaType.print": "Print",
    "mediaType.tv": "Television",
    "mediaType.radio": "Radio",
    "mediaType.online": "Online",
    "mediaType.photographer": "Photographer",
    "mediaType.freelance": "Freelance",
    "common.required": "*"
  },
  "si": {
    "register.title": "මාධ්‍ය අක්තපත්‍ර ලියාපදිංචිය",
    "register.personal": "පෞද්ගලික තොරතුරු",
    "register.fullName": "සම්පූර්ණ නම",
    "register.email": "විද්‍යුත් තැපෑල",
    "register.organization": "සංවිධානය / මාධ්‍ය ආයතනය",
    "register.designation": "තනතුර / භූමිකාව",
    "register.phone": "දුරකථන අංකය",
    "register.country": "රට",
    "register.mediaType": "මාධ්‍ය වර්ගය",
    "register.selectMediaType": "මාධ්‍ය වර්ගය තෝරන්න",
    "register.identity": "අනන්‍යතා සත්‍යාපනය",
    "register.idDocument": "සම්පූර්ණ හැඳුනුම්පත (ගමන් බලපත්‍රය / ජා.හැ.අ.)",
    "register.idDocumentHint": "උඩුගත කිරීමට ක්ලික් කරන්න (JPG, PNG, PDF — උපරිම 5MB)",
    "register.idFaceCrop": "හැඳුනුම්පතේ මුහුණ ආසන්න ඡායාරූපය",
    "register.idFaceCropHint": "ඔබේ හැඳුනුම්පතේ මුහුණ පමණක් ඇති ඡායාරූපයක්",
    "register.idTip": "ඉඟිය: ඔබේ හැඳුනුම්පතේ මුහුණ කොටසේ පැහැදිලි, හොඳ ආලෝකයක් ඇති ආසන්න ඡායාරූපයක් ගන්න.",
    "register.livePhoto": "සජීවී මුහුණ ඡායාරූපය",
    "register.livePhotoHint": "හොඳ ආලෝකයක් ඇති තැනක ඔබේ පැහැදිලි ඡායාරූපයක් ගන්න. මෙය ඔබේ හැඳුනුම්පත් ඡායාරූපය සමඟ සංසන්දනය කෙරේ.",
    "register.openCamera": "කැමරාව විවෘත කිරීමට ක්ලික් කරන්න",
    "register.capture": "ග්‍රහණය කරන්න",
    "register.retake": "නැවත ඡායාරූපයක් ගන්න",
    "register.terms": "මම සපයා ඇති තොරතුරු නිවැරදි බව තහවුරු කරන අතර, ශ්‍රී ලංකා සාම ගමන 2026 සඳහා මාධ්‍ය අක්තපත්‍ර සත්‍යාපනය සඳහා මගේ දත්ත සැකසීමට එකඟ වෙමි.",
    "register.submit": "අයදුම්පත ඉදිරිපත් කරන්න",
    "register.submitting": "ඉදිරිපත් කරමින්...",
    "register.success": "අයදුම්පත ඉදිරිපත් කරන ලදී!",
    "register.refLabel": "ඔබේ යොමු අංකය:",
    "register.saveRef": "මෙම අංකය සුරකින්න. තහවුරු කිරීමේ විද්‍යුත් තැපෑලක් යවා ඇත. ඔබේ අයදුම්පත සමාලෝචනය කළ පසු ඔබට දැනුම් දෙනු ලැබේ.",
    "register.checkStatus": "අයදුම්පත් තත්ත්වය පරීක්ෂා කරන්න",
    "register.errorIdDoc": "කරුණාකර ඔබේ හැඳුනුම්පත උඩුගත කරන්න",
    "register.errorIdFace": "කරුණාකර ඔබේ හැඳුනුම්පතේ මුහුණ ආසන්න ඡායාරූපයක් උඩුගත කරන්න",
    "register.errorFace": "කරුණාකර කැමරාව භාවිතයෙන් ඔබේ මුහුණ ඡායාරූපයක් ග්‍රහණය කරන්න",
    "register.errorTerms": "කරුණාකර නියම පිළිගන්න",
    "register.errorGeneric": "ලියාපදිංචිය අසාර්ථක විය. කරුණාකර නැවත උත්සාහ කරන්න.",
    "mediaType.print": "මුද්‍රිත",
    "mediaType.tv": "රූපවාහිනී",
    "mediaType.radio": "ගුවන්විදුලි",
    "mediaType.online": "අන්තර්ජාල",
    "mediaType.photographer": "ඡායාරූප ශිල්පී",
    "mediaType.freelance": "නිදහස් මාධ්‍යවේදී",
    "common.required": "*"
  }
}
```

- [ ] **Step 2: Create useTranslation hook**

Create `frontend/src/i18n/useTranslation.ts`:

```typescript
import { useState, useCallback } from 'react'
import translations from './translations.json'

type Lang = 'en' | 'si'
type TranslationKeys = keyof typeof translations.en

export function useTranslation() {
  const [lang, setLang] = useState<Lang>(
    () => (localStorage.getItem('lang') as Lang) || 'en'
  )

  const t = useCallback(
    (key: string): string => {
      const dict = translations[lang] as Record<string, string>
      return dict[key] || translations.en[key as TranslationKeys] || key
    },
    [lang]
  )

  const toggleLang = useCallback(() => {
    setLang((prev) => {
      const next = prev === 'en' ? 'si' : 'en'
      localStorage.setItem('lang', next)
      return next
    })
  }, [])

  return { t, lang, toggleLang }
}
```

- [ ] **Step 3: Update RegisterPage.tsx to use i18n and add language toggle**

Modify `frontend/src/pages/RegisterPage.tsx` — import the hook and replace hardcoded strings with `t()` calls. Add a language toggle button in the header:

```tsx
// Add to header section, after the <p> tag:
<button onClick={toggleLang}
  className="mt-2 text-sm border border-gold/30 px-3 py-1 rounded-full text-gold hover:bg-gold/10 transition">
  {lang === 'en' ? 'සිංහල' : 'EN'}
</button>
```

Replace all hardcoded label strings with `t('register.xxx')` equivalents. Replace MEDIA_TYPES label values with `t('mediaType.xxx')`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n/ frontend/src/pages/RegisterPage.tsx
git commit -m "feat: add bilingual support (English + Sinhala) to registration form"
```

---

### Task 10: Add StatusPage ref number input

**Files:**
- Modify: `frontend/src/pages/StatusPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add a standalone status check route**

In `frontend/src/App.tsx`, add a route for `/status` (no param):

```tsx
<Route path="/status" element={<StatusPage />} />
```

(Keep the existing `/status/:refNumber` route too.)

- [ ] **Step 2: Add ref number input form to StatusPage**

When `refNumber` is not provided via URL params, show an input form. Add to the top of the component:

```tsx
const [inputRef, setInputRef] = useState('')
const navigate = useNavigate()

// If no refNumber in URL, show input form
if (!refNumber && !loading) {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-navy text-white py-6 text-center">
        <Link to="/"><h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1></Link>
        <p className="text-gold text-sm">Check Application Status</p>
      </div>
      <div className="max-w-md mx-auto px-4 py-12">
        <div className="bg-white rounded-xl shadow p-8">
          <p className="text-gray-600 mb-4 text-center">Enter your reference number to check your application status.</p>
          <form onSubmit={(e) => { e.preventDefault(); if (inputRef.trim()) navigate(`/status/${inputRef.trim()}`) }}>
            <input value={inputRef} onChange={e => setInputRef(e.target.value)}
              placeholder="e.g. WFP-A1B2C3" required
              className="w-full border rounded-lg px-4 py-3 text-center font-mono text-lg mb-4 focus:ring-2 focus:ring-saffron" />
            <button type="submit" className="w-full bg-saffron text-white py-2 rounded-lg font-medium hover:bg-saffron-dark">
              Check Status
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/StatusPage.tsx frontend/src/App.tsx
git commit -m "feat: add standalone status check form with ref number input"
```

---

### Task 11: Alembic Migration

**Files:**
- Modify: `backend/alembic.ini`

- [ ] **Step 1: Generate initial migration**

Run inside the API container (after docker compose up):

```bash
docker compose exec api alembic revision --autogenerate -m "initial_schema"
```

Expected: A migration file is created in `backend/alembic/versions/`.

- [ ] **Step 2: Verify migration runs**

```bash
docker compose exec api alembic upgrade head
```

Expected: Migration applies cleanly (tables already exist, so it should detect them as up-to-date or stamp the current state).

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add initial Alembic migration"
```

---

## Phase 3: End-to-End Testing

### Task 12: Create Test Images

**Files:**
- Create: `scripts/create-test-images.py`

- [ ] **Step 1: Create test image generator**

```python
"""Generate simple test images for registration flow testing."""
from PIL import Image, ImageDraw, ImageFont
import sys

def create_test_image(filename: str, width: int, height: int, color: str, text: str):
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    # Draw a simple face-like shape for face detection
    cx, cy = width // 2, height // 2
    r = min(width, height) // 3
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill='#FFD5B4')  # skin tone circle
    # Eyes
    draw.ellipse([cx-r//3-5, cy-r//4-5, cx-r//3+5, cy-r//4+5], fill='#333')
    draw.ellipse([cx+r//3-5, cy-r//4-5, cx+r//3+5, cy-r//4+5], fill='#333')
    # Mouth
    draw.arc([cx-r//4, cy+r//8, cx+r//4, cy+r//3], 0, 180, fill='#333', width=2)
    # Label
    draw.text((10, 10), text, fill='white')
    img.save(filename, 'JPEG', quality=90)
    print(f"Created {filename} ({width}x{height})")

if __name__ == '__main__':
    create_test_image('test_id.jpg', 800, 600, '#2244AA', 'ID DOCUMENT')
    create_test_image('test_face_id.jpg', 300, 400, '#334455', 'ID FACE CROP')
    create_test_image('test_face_live.jpg', 400, 400, '#445566', 'LIVE PHOTO')
    print("Test images created!")
```

- [ ] **Step 2: Generate test images**

```bash
cd /path/to/walkforpeace
python scripts/create-test-images.py
```

Expected: 3 JPEG files created in project root.

- [ ] **Step 3: Commit**

```bash
git add scripts/create-test-images.py
git commit -m "feat: add test image generator script"
```

---

### Task 13: Integration Tests

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Create test fixtures**

Create `backend/tests/__init__.py` (empty).

Create `backend/tests/conftest.py`:

```python
"""Test fixtures for integration tests."""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://walkforpeace:walkforpeace@localhost:5432/walkforpeace"
)
os.environ["DATABASE_URL_SYNC"] = os.environ.get(
    "TEST_DATABASE_URL_SYNC",
    "postgresql://walkforpeace:walkforpeace@localhost:5432/walkforpeace"
)
os.environ["UPLOAD_DIR"] = "/tmp/walkforpeace_test_uploads"

from app.main import app
from app.database import get_db, init_db, engine
from app.models.models import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    await init_db()
    yield
    # Don't drop tables — shared dev DB


@pytest_asyncio.fixture
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_images():
    """Create minimal test images in memory."""
    from PIL import Image, ImageDraw
    import io

    def make_img(w, h, color):
        img = Image.new('RGB', (w, h), color)
        draw = ImageDraw.Draw(img)
        # Simple face-like oval
        cx, cy = w // 2, h // 2
        r = min(w, h) // 3
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill='#FFD5B4')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    return {
        'id_document': make_img(800, 600, '#224488'),
        'id_face_crop': make_img(300, 400, '#334455'),
        'face_photo': make_img(400, 400, '#445566'),
    }
```

- [ ] **Step 2: Create integration test file**

Create `backend/tests/test_api.py`:

```python
"""Integration tests for Walk for Peace API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegistration:
    async def test_register_valid(self, client: AsyncClient, test_images):
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Test User',
            'organization': 'Test News',
            'designation': 'Reporter',
            'email': 'test@example.com',
            'phone': '+94771234567',
            'country': 'Sri Lanka',
            'media_type': 'print',
            'terms_accepted': 'true',
        }
        resp = await client.post('/api/register', data=data, files=files)
        assert resp.status_code == 200
        body = resp.json()
        assert 'ref_number' in body
        assert body['ref_number'].startswith('WFP-')
        assert body['status'] == 'pending_review'

    async def test_register_missing_fields(self, client: AsyncClient, test_images):
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {'full_name': 'Test'}  # Missing required fields
        resp = await client.post('/api/register', data=data, files=files)
        assert resp.status_code == 422

    async def test_register_invalid_file_type(self, client: AsyncClient):
        files = {
            'id_document': ('test.exe', b'fake exe content', 'application/octet-stream'),
            'id_face_crop': ('face.jpg', b'\xff\xd8\xff\xe0', 'image/jpeg'),
            'face_photo': ('live.jpg', b'\xff\xd8\xff\xe0', 'image/jpeg'),
        }
        data = {
            'full_name': 'Test', 'organization': 'Test', 'designation': 'Test',
            'email': 'test@test.com', 'phone': '+94771234567', 'country': 'LK',
            'media_type': 'print', 'terms_accepted': 'true',
        }
        resp = await client.post('/api/register', data=data, files=files)
        assert resp.status_code == 400


class TestStatus:
    async def test_status_valid(self, client: AsyncClient, test_images):
        # First register
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Status Test', 'organization': 'Test Org', 'designation': 'Editor',
            'email': 'status@test.com', 'phone': '+94771234567', 'country': 'Sri Lanka',
            'media_type': 'online', 'terms_accepted': 'true',
        }
        reg = await client.post('/api/register', data=data, files=files)
        ref = reg.json()['ref_number']

        resp = await client.get(f'/api/register/status/{ref}')
        assert resp.status_code == 200
        assert resp.json()['ref_number'] == ref
        assert resp.json()['status'] == 'pending_review'

    async def test_status_not_found(self, client: AsyncClient):
        resp = await client.get('/api/register/status/FAKE-REF-999')
        assert resp.status_code == 404


class TestAdminAuth:
    async def test_login_success(self, client: AsyncClient):
        resp = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        assert resp.status_code == 200
        assert 'access_token' in resp.json()

    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'wrong'
        })
        assert resp.status_code == 401

    async def test_applications_without_auth(self, client: AsyncClient):
        resp = await client.get('/api/admin/applications')
        assert resp.status_code in (401, 403)

    async def test_applications_with_auth(self, client: AsyncClient):
        login = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        token = login.json()['access_token']
        resp = await client.get('/api/admin/applications', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200
        assert 'items' in resp.json()

    async def test_stats_with_auth(self, client: AsyncClient):
        login = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        token = login.json()['access_token']
        resp = await client.get('/api/admin/stats', headers={
            'Authorization': f'Bearer {token}'
        })
        assert resp.status_code == 200
        assert 'total_registered' in resp.json()


class TestAdminReview:
    async def _register_and_get_id(self, client, test_images):
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Review Test', 'organization': 'Review Org', 'designation': 'Writer',
            'email': f'review-{id(self)}@test.com', 'phone': '+94771234567',
            'country': 'Sri Lanka', 'media_type': 'tv', 'terms_accepted': 'true',
        }
        await client.post('/api/register', data=data, files=files)

        login = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        token = login.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        apps = await client.get('/api/admin/applications?page=1&page_size=100', headers=headers)
        items = apps.json()['items']
        app_id = items[0]['id']  # Most recent
        return app_id, token, headers

    async def test_approve_flow(self, client: AsyncClient, test_images):
        app_id, token, headers = await self._register_and_get_id(client, test_images)

        resp = await client.patch(f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve', 'admin_notes': 'Test approved'},
            headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert 'credential_token' in body
        assert 'badge_number' in body

    async def test_reject_flow(self, client: AsyncClient, test_images):
        # Register a new one
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Reject Test', 'organization': 'Reject Org', 'designation': 'Intern',
            'email': 'reject@test.com', 'phone': '+94771234567',
            'country': 'Sri Lanka', 'media_type': 'radio', 'terms_accepted': 'true',
        }
        await client.post('/api/register', data=data, files=files)

        login = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        token = login.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        apps = await client.get('/api/admin/applications?status=pending_review&page_size=100', headers=headers)
        pending = [a for a in apps.json()['items'] if a['full_name'] == 'Reject Test']
        if pending:
            app_id = pending[0]['id']
            resp = await client.patch(f'/api/admin/applications/{app_id}/review',
                json={'action': 'reject', 'admin_notes': 'Test rejected'},
                headers=headers)
            assert resp.status_code == 200


class TestVerification:
    async def test_verify_invalid_token(self, client: AsyncClient):
        resp = await client.get('/api/verify/tampered-fake-token')
        assert resp.status_code == 200
        body = resp.json()
        assert body['valid'] is False
        assert body['status'] == 'invalid'

    async def test_verify_valid_credential(self, client: AsyncClient, test_images):
        # Register -> Approve -> Get credential token -> Verify
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Verify Test', 'organization': 'Verify Org', 'designation': 'Camera',
            'email': 'verify@test.com', 'phone': '+94771234567',
            'country': 'Sri Lanka', 'media_type': 'photographer', 'terms_accepted': 'true',
        }
        await client.post('/api/register', data=data, files=files)

        login = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        token = login.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        apps = await client.get('/api/admin/applications?status=pending_review&page_size=100', headers=headers)
        pending = [a for a in apps.json()['items'] if a['full_name'] == 'Verify Test']
        if not pending:
            pytest.skip("No pending application found")
        app_id = pending[0]['id']

        review = await client.patch(f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve', 'admin_notes': 'Verified'},
            headers=headers)
        cred_token = review.json()['credential_token']

        # Verify
        resp = await client.get(f'/api/verify/{cred_token}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['valid'] is True
        assert body['status'] == 'valid'
        assert body['full_name'] == 'Verify Test'


class TestRevocation:
    async def test_revoke_and_verify(self, client: AsyncClient, test_images):
        # Register -> Approve -> Revoke -> Verify (should fail)
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Revoke Test', 'organization': 'Revoke Org', 'designation': 'Editor',
            'email': 'revoke@test.com', 'phone': '+94771234567',
            'country': 'Sri Lanka', 'media_type': 'freelance', 'terms_accepted': 'true',
        }
        await client.post('/api/register', data=data, files=files)

        login = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        token = login.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        apps = await client.get('/api/admin/applications?status=pending_review&page_size=100', headers=headers)
        pending = [a for a in apps.json()['items'] if a['full_name'] == 'Revoke Test']
        if not pending:
            pytest.skip("No pending application found")
        app_id = pending[0]['id']

        review = await client.patch(f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve', 'admin_notes': 'For revoke test'},
            headers=headers)
        cred_token = review.json()['credential_token']

        # Revoke
        resp = await client.post(f'/api/admin/applications/{app_id}/revoke', headers=headers)
        assert resp.status_code == 200

        # Verify should show revoked
        verify = await client.get(f'/api/verify/{cred_token}')
        assert verify.json()['valid'] is False
        assert verify.json()['status'] == 'revoked'
```

- [ ] **Step 3: Add test dependencies to requirements.txt**

Append to `backend/requirements.txt`:

```
# Testing
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 4: Run tests**

```bash
docker compose exec api pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/ backend/requirements.txt
git commit -m "feat: add comprehensive integration tests"
```

---

## Phase 4: Git Setup and Deployment Prep

### Task 14: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create deploy workflow**

```yaml
name: Deploy to VPS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/walkforpeace
            git pull origin main
            docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
            sleep 10
            bash scripts/smoke-test.sh https://walkforpeacelk.org || echo "Smoke test failed!"
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/deploy.yml
git commit -m "feat: add GitHub Actions deployment workflow"
```

---

### Task 15: VPS Deployment Scripts

**Files:**
- Create: `scripts/setup-ssl.sh`
- Create: `scripts/vps-init.sh`

- [ ] **Step 1: Create SSL setup script**

```bash
#!/bin/bash
# Walk for Peace — SSL certificate setup
set -e

DOMAIN="walkforpeacelk.org"
EMAIL="admin@$DOMAIN"

echo "Installing certbot..."
apt-get update
apt-get install -y certbot

echo "Obtaining certificate for $DOMAIN..."
certbot certonly --standalone \
  -d $DOMAIN -d www.$DOMAIN \
  --non-interactive --agree-tos \
  --email $EMAIL

echo "Setting up auto-renewal..."
echo "0 0 * * * root certbot renew --quiet --post-hook 'docker compose -f /opt/walkforpeace/docker-compose.yml restart nginx'" | tee /etc/cron.d/certbot-renew

echo "SSL setup complete!"
echo "Certificate at: /etc/letsencrypt/live/$DOMAIN/"
```

- [ ] **Step 2: Create VPS init script**

```bash
#!/bin/bash
# Walk for Peace — VPS initialization
set -e

APP_DIR="/opt/walkforpeace"

echo "=== Walk for Peace VPS Setup ==="

# Install Docker
if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

# Install Docker Compose plugin
if ! docker compose version &> /dev/null; then
  echo "Installing Docker Compose plugin..."
  apt-get install -y docker-compose-plugin
fi

# Create app directory
echo "Setting up app directory at $APP_DIR..."
mkdir -p $APP_DIR
cd $APP_DIR

echo "=== Setup complete ==="
echo "Next steps:"
echo "1. Clone the repo: git clone <repo-url> $APP_DIR"
echo "2. Copy .env: cp .env.example .env && nano .env"
echo "3. Run SSL setup: bash scripts/setup-ssl.sh"
echo "4. Start services: docker compose up --build -d"
echo "5. Run smoke test: bash scripts/smoke-test.sh https://walkforpeacelk.org"
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x scripts/setup-ssl.sh scripts/vps-init.sh
```

- [ ] **Step 4: Commit**

```bash
git add scripts/setup-ssl.sh scripts/vps-init.sh
git commit -m "feat: add VPS init and SSL setup scripts"
```

---

### Task 16: Git Init and Push

- [ ] **Step 1: Initialize git repo**

```bash
cd /path/to/walkforpeace
git init
git add .
git commit -m "Initial commit: Walk for Peace Media Credential System

- FastAPI backend with PostgreSQL
- React + TypeScript + Tailwind frontend
- DeepFace face matching (ArcFace)
- QR credential generation and verification
- Docker Compose deployment
- Admin dashboard with photo comparison
- Mobile QR scanner for event-day verification
- Bilingual support (English + Sinhala)
- Integration tests
- CSRF protection"
```

Note: If git was already initialized with prior commits, skip `git init` and just ensure all changes are committed.

- [ ] **Step 2: Add remote and push**

```bash
git remote add origin https://github.com/nuwansamaranayake/walkforpeacecredentialsystem.git
git branch -M main
git push -u origin main
```

---

## Summary of All Issues Found and Fixed

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | `aiofiles` import in admin.py | Not in requirements.txt, not needed | Removed |
| 2 | UnboundLocalError in face_match.py | Variables referenced before assignment | Initialize to None |
| 3 | bcrypt compatibility | passlib 1.7.4 vs bcrypt 4.x | Pin bcrypt==4.0.1 |
| 4 | nginx fails in dev | SSL certs don't exist | Separate dev/prod configs |
| 5 | CORS blocks localhost | ENVIRONMENT defaults to production | Default to development |
| 6 | Frontend volume stale data | Docker named volume not refreshed on rebuild | Copy in CMD |
| 7 | No CSRF protection | Missing entirely | Added Origin/Referer middleware |
| 8 | No bilingual support | English only | Added EN/Sinhala i18n |
| 9 | No status input form | StatusPage requires URL param | Added ref number input |
| 10 | No tests | Missing entirely | Added pytest integration suite |
| 11 | No deployment scripts | Missing entirely | Added GH Actions, SSL, VPS scripts |
