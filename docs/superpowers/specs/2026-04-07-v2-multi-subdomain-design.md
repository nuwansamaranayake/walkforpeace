# Walk for Peace v2 — Multi-Subdomain Architecture Design

**Date:** 2026-04-07
**Status:** Approved
**Repo:** nuwansamaranayake/walkforpeace (branch: v2-multi-subdomain)

---

## 1. Architecture Overview

Three subdomains, one API backend, three frontend builds:

```
register.walkforpeacelk.com  →  Media personnel (public)
verify.walkforpeacelk.com    →  Security staff at event (password-protected)
admin.walkforpeacelk.com     →  Organizing committee (JWT auth)
```

All three hit the same FastAPI backend. Each subdomain is a separate Vite/React build served by nginx via `server_name` routing. API calls proxy through nginx to the backend.

```
                         ┌─────────────────┐
                         │   nginx:alpine   │
                         │ (3 server blocks)│
                         └──────┬──────────┘
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              register       verify       admin
             (React SPA)   (React SPA)  (React SPA)
                    └───────────┼───────────┘
                                ▼
                          /api/* proxy
                                │
                         ┌──────▼──────┐
                         │   FastAPI   │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  PostgreSQL  │
                         └─────────────┘
```

**Docker Compose services:** postgres, api, register, verify, admin, nginx (6 total).

### What carries forward from v1

- All backend services (auth, storage, face_match, badge, qr, email)
- Database models (extended, not replaced)
- Admin API routes (mostly unchanged)
- Registration API routes (extended with PIN + OCR)
- Verification API route (enhanced payload)
- CSRF middleware, config, database setup
- Integration test infrastructure (HTTP-based against live Docker)

### What's new

- 5 new DB columns on media_applications
- 1 new table (verify_sessions)
- verification_status on credentials (distinct from application status)
- verified_by_action on verification_logs
- 7 new API endpoints, 5 modified endpoints
- Three separate frontend Vite projects with npm workspaces
- Multi-subdomain nginx config
- OCR endpoint (pytesseract, NIC number extraction)

---

## 2. Database Schema Changes

### media_applications — ADD 5 columns

```sql
pin_code            VARCHAR(20)   UNIQUE NOT NULL  -- "WFP-482917"
id_number           VARCHAR(50)   INDEXED          -- NIC or passport number
id_type             VARCHAR(20)   DEFAULT 'nic'    -- "nic" | "passport"
ocr_extracted_name  VARCHAR(200)  NULLABLE         -- best-effort OCR
ocr_extracted_id    VARCHAR(50)   NULLABLE         -- best-effort OCR NIC number
```

- `pin_code`: generated at registration (not approval). Format: `WFP-` + 6 random digits. Unique at DB level.
- `id_number`: powers "Get QR by NIC/passport" lookup. Indexed for fast queries.
- `id_type`: defaults to "nic". Frontend sends based on user selection.
- OCR fields: advisory only, stored for admin comparison.

### credentials — ADD 1 column, CHANGE behavior

```sql
verification_status VARCHAR(20) DEFAULT 'pending'
-- Values: pending | approved | flagged | rejected | revoked
```

**Behavior change:** Credentials generated for ALL registrations at submit time (not just approved). `verification_status` controls what QR scan shows. Distinct from `media_applications.status` (admin review workflow).

- Admin approve → verification_status = 'approved'
- Admin reject → verification_status = 'rejected'
- Face match < 60% → verification_status = 'flagged'
- Revoke → verification_status = 'revoked'

### verification_logs — ADD 1 column

```sql
verified_by_action VARCHAR(20) NULLABLE
-- null | "gate_approved" | "gate_denied"
```

Records security officer gate resolutions for flagged credentials.

### verify_sessions — NEW TABLE

```sql
id              UUID PRIMARY KEY
session_token   VARCHAR(200) UNIQUE NOT NULL
created_at      TIMESTAMP DEFAULT now()
expires_at      TIMESTAMP NOT NULL
device_ip       VARCHAR(50)
```

Created when security officer enters shared event-day password. Default expiry: 24 hours (VERIFY_SESSION_HOURS env var). No user accounts — anonymous sessions.

### Migration approach

Single Alembic revision. Two-phase within the same revision:
1. Add columns as nullable, backfill pin_code for existing rows (generate unique PINs), backfill verification_status from application status
2. Then add UNIQUE NOT NULL constraint on pin_code

This ensures the constraint is applied after all existing rows have values.

---

## 3. API Changes

### Registration endpoints (register.walkforpeacelk.com)

**POST /api/register — MODIFIED**

Now generates pin_code + credential + QR immediately at registration. Response:
```json
{
  "ref_number": "WFP-XXXXXX",
  "pin_code": "WFP-482917",
  "status": "pending_review",
  "qr_code_url": "/uploads/qr/xxx.png",
  "message": "Application submitted successfully"
}
```

Flow:
1. Validate form + files → create MediaApplication with pin_code
2. Upload files to storage
3. Create Credential immediately (verification_status = 'pending')
4. Generate QR code (encodes credential token)
5. Run face match in background → if < 60%, update to verification_status = 'flagged'
6. Send confirmation email with PIN
7. Return ref_number, pin_code, qr_code_url

**GET /api/register/status/{ref_number} — UNCHANGED**

**GET /api/register/retrieve — NEW**

Query: `?pin=WFP-482917` OR `?id_number=200370312725`

Response varies by verification_status:
- approved → QR code URL + badge details + download option
- pending → "Application under review" + PIN + ref_number
- flagged → "Under review — bring original ID to event" + QR code (still works)
- rejected → rejection message + admin notes if any
- not found → 404

**POST /api/register/ocr — NEW**

Accepts single image upload. Runs pytesseract. Extracts:
- NIC number: 12-digit regex pattern (primary target, reliable)
- Name: best-effort from "Name:" field on NIC card (secondary, flaky)
- Passport number: minimal parsing (low priority)

Returns: `{id_number: "200370312725", name: "KAMAL PERERA", confidence: "high"|"low"|null}`

Fails gracefully → returns empty fields, never blocks registration.

### Verification endpoints (verify.walkforpeacelk.com)

**POST /api/verify/auth — NEW**

Body: `{password: "Peace2026Verify"}`
Validates against VERIFY_PASSWORD env var.
Returns: `{session_token: "...", expires_at: "..."}`
Creates verify_sessions row.

**GET /api/verify/{credential_token} — MODIFIED**

Tiered response based on session:

Without verify session (public — called from register "Get QR" flow):
```json
{
  "valid": true,
  "status": "approved",
  "full_name": "...",
  "organization": "...",
  "media_type": "...",
  "badge_number": "...",
  "face_photo_url": "...",
  "message": "..."
}
```

With valid verify session (security officer — full payload):
```json
{
  "valid": true,
  "verification_status": "flagged",
  "full_name": "...",
  "organization": "...",
  "media_type": "...",
  "designation": "...",
  "face_photo_url": "...",
  "id_face_crop_url": "...",
  "face_match_score": 0.573,
  "badge_number": "...",
  "can_gate_approve": true,
  "message": "..."
}
```

Session token optional. Sensitive fields (id_face_crop_url, face_match_score, can_gate_approve) only included with valid session.

**POST /api/verify/{credential_token}/gate-approve — NEW**

Requires verify session. Sets verification_status = 'approved'. Logs verified_by_action = 'gate_approved'. Next scan shows green.

**POST /api/verify/{credential_token}/gate-deny — NEW**

Requires verify session. Does NOT change verification_status (admin handles). Logs verified_by_action = 'gate_denied'.

### Admin endpoints (admin.walkforpeacelk.com)

**POST /api/admin/login — UNCHANGED**
**POST /api/admin/refresh — UNCHANGED**
**POST /api/admin/change-password — UNCHANGED**

**GET /api/admin/applications — MODIFIED**
Add filter: `?flagged=true`. Response includes pin_code, id_number.

**GET /api/admin/applications/{id} — MODIFIED**
Response includes OCR fields (ocr_extracted_name, ocr_extracted_id) for comparison with submitted data.

**PATCH /api/admin/applications/{id}/review — MODIFIED**
On approve → sets credential.verification_status = 'approved' (credential already exists).
On reject → sets verification_status = 'rejected'.
No longer creates credential — it already exists from registration.

**POST /api/admin/applications/{id}/revoke — MODIFIED**
Sets verification_status = 'revoked'.

**POST /api/admin/applications/batch-approve — NEW**
Body: `{application_ids: [...]}`
Approves multiple pending applications. Sets all credentials to verification_status = 'approved'. Sends credential emails. Returns count.

**GET /api/admin/verification-logs — NEW**
Query: `?credential_id=X&date_from=&date_to=&page=&page_size=`
Returns paginated scan logs with timestamps, IPs, results, gate actions.

**GET /api/admin/stats — MODIFIED**
Add flagged_face_match count to response.

### CORS

Allow all three subdomains:
```
https://register.walkforpeacelk.com
https://verify.walkforpeacelk.com
https://admin.walkforpeacelk.com
```
Plus localhost variants (localhost:5173, localhost:5174, localhost:5175, localhost:8000) in development.

---

## 4. Frontend Architecture

### Directory structure

```
frontend/
├── package.json               # Root — npm workspaces declaration
├── shared/                    # @walkforpeace/shared
│   ├── package.json
│   ├── types.ts               # All TypeScript interfaces
│   ├── api.ts                 # Axios instance + all API functions
│   └── components/            # LanguageToggle, StatusBadge, Logo
│
├── register/                  # register.walkforpeacelk.com
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx            # Routes: /, /register, /get-qr, /status/:ref
│       ├── pages/
│       │   ├── LandingPage.tsx      # Two buttons: Register / Get QR
│       │   ├── RegisterPage.tsx     # Form + camera + OCR (from v1, enhanced)
│       │   ├── GetQRPage.tsx        # PIN/NIC/passport lookup → QR display
│       │   ├── ConfirmationPage.tsx # Post-submit: PIN prominently displayed
│       │   └── StatusPage.tsx       # Status check (from v1)
│       ├── components/
│       │   ├── CameraCapture.tsx    # WebRTC face capture
│       │   └── OCRUpload.tsx        # Upload ID → OCR → auto-fill
│       └── i18n/                    # EN + Sinhala (from v1)
│
├── verify/                    # verify.walkforpeacelk.com
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx            # Routes: /, /scan
│       ├── pages/
│       │   ├── PasswordPage.tsx     # Single password field → session
│       │   └── ScanPage.tsx         # QR scanner + result display
│       └── components/
│           ├── QRScanner.tsx        # html5-qrcode wrapper
│           ├── ResultApproved.tsx   # Green card (Option B — white bg, color stripe)
│           ├── ResultFlagged.tsx    # Amber card + tap-and-hold approve/deny
│           └── ResultRejected.tsx   # Red card
│
├── admin/                     # admin.walkforpeacelk.com
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx            # Routes: /, /dashboard, /review/:id, /logs
│       ├── pages/
│       │   ├── LoginPage.tsx        # JWT login (from v1)
│       │   ├── DashboardPage.tsx    # Stats + app list (from v1, enhanced)
│       │   ├── ReviewPage.tsx       # Detail review (from v1, add OCR comparison)
│       │   └── LogsPage.tsx         # Verification scan logs (NEW)
│       └── components/
│           ├── ApplicationTable.tsx # Filterable table with batch select
│           └── FaceComparison.tsx   # Side-by-side ID vs live face
```

### Dependencies per build

| Dependency | register | verify | admin |
|---|---|---|---|
| react, react-dom, react-router-dom | ✓ | ✓ | ✓ |
| axios | ✓ | ✓ | ✓ |
| tailwindcss | ✓ | ✓ | ✓ |
| react-webcam | ✓ | ✗ | ✗ |
| html5-qrcode | ✗ | ✓ | ✗ |
| lucide-react | ✓ | ✗ | ✓ |

Verify bundle target: ~80KB gzipped. Admin: ~200KB+.

### Shared code strategy

npm workspaces. Root `frontend/package.json` declares workspaces: `["shared", "register", "verify", "admin"]`. Each app imports from `@walkforpeace/shared`. Vite tree-shakes to only what each app uses.

### Bilingual scope

Only register subdomain gets EN + Sinhala. Verify and admin are English-only.

### Verify UI design decisions

- **Option B (Card Style):** White background with thick color stripe at top. High contrast for sunlight readability on budget Android screens.
- **Gate-approve confirmation:** Tap-and-hold for 2 seconds (progress indicator fills). No password re-entry. Prevents accidental taps, fast enough for queue throughput.
- Three result components: ResultApproved (green), ResultFlagged (amber with approve/deny), ResultRejected (red).

### Branding

- Primary: saffron orange #E8930A
- Secondary: deep navy #1B2A4A
- Accent: gold #F5C563
- Consistent across all three subdomains

---

## 5. Infrastructure

### Docker Compose — 6 services

```yaml
services:
  postgres:     # Unchanged
  api:          # Add VERIFY_PASSWORD, VERIFY_SESSION_HOURS, CORS_ORIGINS env vars
  register:     # NEW — builds frontend/register
  verify:       # NEW — builds frontend/verify
  admin:        # NEW — builds frontend/admin (replaces old "frontend")
  nginx:        # MODIFIED — three server blocks
```

Frontend Dockerfiles: same copy-on-start pattern as v1.
```
Stage 1: node:20-alpine → npm ci (workspace-aware) → npm run build
Stage 2: alpine:3.19 → copy dist → CMD copies to shared volume
```

### Volumes

```yaml
volumes:
  pgdata:           # unchanged
  uploads:          # unchanged
  register_build:   # NEW
  verify_build:     # NEW
  admin_build:      # NEW
```

nginx mounts:
```
register_build → /usr/share/nginx/html/register
verify_build   → /usr/share/nginx/html/verify
admin_build    → /usr/share/nginx/html/admin
```

### Nginx — development (HTTP)

Three server blocks by server_name, all port 80. Plus fallback default_server serving register frontend (so localhost:80 works without /etc/hosts).

Local testing requires /etc/hosts entries:
```
127.0.0.1  register.walkforpeacelk.com verify.walkforpeacelk.com admin.walkforpeacelk.com
```

### Nginx — production (SSL)

Three individual Let's Encrypt certs via HTTP-01 challenge (simpler than wildcard). Updated ssl-setup.sh accepts multiple subdomains.

### New environment variables

```
VERIFY_PASSWORD=Peace2026Verify
VERIFY_SESSION_HOURS=24
CORS_ORIGINS=http://register.walkforpeacelk.com,http://verify.walkforpeacelk.com,http://admin.walkforpeacelk.com
```

### GitHub Actions

CI job unchanged (tests against postgres + api only). Deploy job unchanged (SSH + docker compose build).

### DNS (user creates A records)

```
register.walkforpeacelk.com  →  187.127.135.82
verify.walkforpeacelk.com    →  187.127.135.82
admin.walkforpeacelk.com     →  187.127.135.82
```

---

## 6. Testing & Rollout

### Integration tests — 34 total

Existing 16 tests carry forward (updated where registration response changes). 18 new tests:

- TestPINRetrieval (4): retrieve by PIN found/not found, retrieve by NIC found/not found
- TestOCR (2): valid NIC image extraction, garbage image graceful failure
- TestVerifyAuth (3): correct password → session, wrong password → 401, expired → 401
- TestVerifySession (3): scan with session (full payload), without (public only), expired
- TestGateApprove (3): gate-approve flagged → green, gate-deny → logged, gate-approve non-flagged → 400
- TestBatchApprove (2): batch approve multiple, batch with invalid IDs
- TestVerificationLogs (1): logs with gate actions

### Smoke test script — 22 steps

Extended from v1's 10-step flow. Covers: registration with PIN, QR retrieval by PIN and NIC, OCR, admin review, verify session auth, flagged gate-approve, revocation, batch approve, verification logs, subdomain routing.

### Rollout sequence

1. Branch `v2-multi-subdomain` from main
2. Backend: schema migration → new endpoints → updated endpoints → curl verification
3. Frontend: restructure into three builds → shared workspace → carry forward v1 pages
4. Infrastructure: docker-compose → nginx → build verification
5. Test: full smoke test + pytest (34 tests)
6. Merge to main, push
7. Deploy: DNS A records → SSL certs → docker compose up on VPS
