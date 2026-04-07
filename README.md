# Walk for Peace Sri Lanka 2026 — Media Credential Management System

Secure registration, verification, and access control for ~250 media personnel covering the Walk for Peace.

## Architecture

- **Backend**: Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL
- **Frontend**: React 18 / TypeScript / Tailwind CSS / Vite
- **Infrastructure**: Docker Compose (nginx + api + frontend + postgres)
- **Face Matching**: DeepFace with ArcFace model
- **QR Verification**: Cryptographically signed JWT tokens

## Quick Start (Development)

```bash
# Copy and configure environment
cp .env.example .env

# Start all services
docker compose up --build

# Access:
# Frontend: http://localhost
# API: http://localhost/api/health
# Admin: http://localhost/admin (admin / WalkForPeace2026!)
```

## Three Interfaces

1. **Registration Portal** (`/register`) — Media personnel self-register with ID upload + live face capture
2. **Admin Dashboard** (`/admin`) — Review applications, approve/reject, generate QR badges
3. **Verification Scanner** (`/verify`) — Security staff scan QR codes at the event

## Image Upload Requirements

Registrants submit **three images**:
- **Full ID document** — Passport or NIC (complete image)
- **ID face close-up** — Cropped photo of just the face from the ID
- **Live face photo** — Captured via device camera (not file upload)

The system compares the ID face crop with the live photo using DeepFace (ArcFace). Applications with <60% match are **flagged** (not rejected) for admin review.

## Smoke Test

```bash
bash scripts/smoke-test.sh http://localhost
```

## Deployment

Target: Hostinger Mumbai VPS at 187.127.135.82

```bash
# On VPS
git pull
docker compose up --build -d
bash scripts/smoke-test.sh https://walkforpeacelk.org
```
