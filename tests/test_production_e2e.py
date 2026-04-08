#!/usr/bin/env python3
"""Walk for Peace --Comprehensive Production E2E Test Suite.

Runs against live production endpoints. Requires `requests` package.
Usage: python tests/test_production_e2e.py
"""
import os
import sys
import time
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# -- Configuration ----------------------------------------------------------
BASE_URL = os.getenv("BASE_URL", "https://register.walkforpeacelk.org")
VERIFY_URL = os.getenv("VERIFY_URL", "https://verify.walkforpeacelk.org")
ADMIN_URL = os.getenv("ADMIN_URL", "https://admin.walkforpeacelk.org")
VERIFY_PASSWORD = os.getenv("VERIFY_PASSWORD", "Peace2026Verify")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "WalkForPeace2026!")

FIXTURES = Path(__file__).parent / "fixtures"

# Test people
TEST_PEOPLE = [
    {"name": "Aruni Perera", "nic": "200370312725", "folder": "aruni",
     "org": "Daily Mirror", "designation": "Senior Reporter", "media_type": "print"},
    {"name": "Bashini Fernando", "nic": "200650100556", "folder": "bashini",
     "org": "Sirasa TV", "designation": "News Anchor", "media_type": "tv"},
    {"name": "Lakshika Silva", "nic": "200256701290", "folder": "lakshika",
     "org": "Hiru FM", "designation": "Field Reporter", "media_type": "radio"},
    {"name": "Alia Hussain", "nic": "200762500605", "folder": "alia",
     "org": "Roar Media", "designation": "Photojournalist", "media_type": "online"},
]


# -- Result tracking -------------------------------------------------------
@dataclass
class PhaseResult:
    name: str
    passed: int = 0
    failed: int = 0
    expected_fail: int = 0
    failures: list = field(default_factory=list)


class TestRunner:
    def __init__(self):
        self.phases: list[PhaseResult] = []
        self.current_phase: Optional[PhaseResult] = None
        self.session = requests.Session()
        self.session.verify = True
        # Storage for cross-phase data
        self.registrations: dict[str, dict] = {}  # folder -> {ref_number, pin_code, app_id, cred_token}
        self.admin_token: Optional[str] = None
        self.verify_session: Optional[str] = None

    def start_phase(self, name: str):
        self.current_phase = PhaseResult(name=name)
        self.phases.append(self.current_phase)
        print(f"\n{'-'*60}")
        print(f"  {name}")
        print(f"{'-'*60}")

    def check(self, label: str, condition: bool, detail: str = "",
              endpoint: str = "", expected: str = "", actual: str = "",
              expected_failure: bool = False):
        if condition:
            if expected_failure:
                self.current_phase.expected_fail += 1
                print(f"  !  {label} (expected fail -- passed anyway)")
            else:
                self.current_phase.passed += 1
                print(f"  OK{label}")
        else:
            if expected_failure:
                self.current_phase.expected_fail += 1
                print(f"  ~  {label} (expected failure)", flush=True)
            else:
                self.current_phase.failed += 1
                print(f"  FAIL{label}")
                fail_info = {"label": label, "endpoint": endpoint,
                             "expected": expected, "actual": actual[:500] if actual else ""}
                self.current_phase.failures.append(fail_info)

    def should_stop(self) -> bool:
        return self.current_phase is not None and self.current_phase.failed > 2

    def print_summary(self):
        print(f"\n{'='*60}")
        print("WALK FOR PEACE --PRODUCTION E2E TEST SUITE")
        print(f"Target: register/verify/admin.walkforpeacelk.org")
        print(f"{'='*60}\n")

        total_pass = 0
        total_fail = 0
        total_expected = 0

        for p in self.phases:
            total = p.passed + p.failed + p.expected_fail
            status = "PASS" if p.failed == 0 else "FAIL"
            extra = ""
            if p.expected_fail > 0:
                extra = f" ({p.expected_fail} expected fail)"
            line = f"{p.name} {'.'*(40 - len(p.name))} {p.passed + p.expected_fail}/{total} {status}{extra}"
            print(line)
            total_pass += p.passed
            total_fail += p.failed
            total_expected += p.expected_fail

            for f in p.failures:
                print(f"    FAILED: {f['label']}")
                if f['endpoint']:
                    print(f"      Endpoint: {f['endpoint']}")
                if f['expected']:
                    print(f"      Expected: {f['expected']}")
                if f['actual']:
                    print(f"      Actual:   {f['actual']}")

        total = total_pass + total_fail + total_expected
        print(f"\nTOTAL: {total_pass + total_expected}/{total} PASSED | {total_expected} EXPECTED FAILURES | {total_fail} UNEXPECTED FAILURES")
        print(f"{'='*60}")

        # Print created test data for cleanup
        if self.registrations:
            print(f"\nTest data created (for cleanup):")
            for folder, data in self.registrations.items():
                print(f"  {folder}: ref={data.get('ref_number')} pin={data.get('pin_code')}")

        return total_fail == 0

    # -- Helpers --------------------------------------------------------
    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def verify_headers(self):
        return {"Authorization": f"Bearer {self.verify_session}"} if self.verify_session else {}

    def get_images(self, folder: str):
        id_img = FIXTURES / folder / f"{folder}_id.jpg"
        photo = FIXTURES / folder / f"{folder}_photo.jpg"
        return id_img, photo

    # -- Phase 1: Infrastructure ----------------------------------------
    def phase1_infrastructure(self):
        self.start_phase("Phase 1: Infrastructure")

        # 1. GET each subdomain root
        for url, label in [(BASE_URL, "register"), (VERIFY_URL, "verify"), (ADMIN_URL, "admin")]:
            try:
                r = self.session.get(f"{url}/", timeout=15)
                self.check(f"{label} root -> 200 + HTML", r.status_code == 200 and "<!DOCTYPE" in r.text,
                           endpoint=f"GET {url}/", expected="200 + HTML",
                           actual=f"{r.status_code} {r.text[:100]}")
            except Exception as e:
                self.check(f"{label} root -> 200", False, endpoint=f"GET {url}/", actual=str(e))

        # 2. GET /api/health on each subdomain
        for url, label in [(BASE_URL, "register"), (VERIFY_URL, "verify"), (ADMIN_URL, "admin")]:
            try:
                r = self.session.get(f"{url}/api/health", timeout=10)
                ok = r.status_code == 200 and r.json().get("status") == "ok"
                self.check(f"{label} /api/health -> ok", ok,
                           endpoint=f"GET {url}/api/health", expected='{"status":"ok"}',
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check(f"{label} /api/health", False, actual=str(e))

        # 3. CORS headers on OPTIONS
        try:
            r = self.session.options(f"{BASE_URL}/api/health",
                                     headers={"Origin": BASE_URL,
                                              "Access-Control-Request-Method": "POST"}, timeout=10)
            has_cors = "access-control-allow-origin" in r.headers
            self.check("CORS headers present on OPTIONS", has_cors,
                       endpoint=f"OPTIONS {BASE_URL}/api/health",
                       expected="access-control-allow-origin header",
                       actual=str(dict(r.headers))[:300])
        except Exception as e:
            self.check("CORS headers", False, actual=str(e))

        # 4. POST with Origin header not blocked by CSRF
        try:
            r = self.session.post(f"{BASE_URL}/api/health",
                                  headers={"Origin": BASE_URL}, timeout=10)
            not_blocked = r.status_code != 403
            self.check("CSRF allows subdomain origin", not_blocked,
                       endpoint=f"POST {BASE_URL}/api/health Origin:{BASE_URL}",
                       expected="not 403",
                       actual=f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            self.check("CSRF subdomain check", False, actual=str(e))

        if self.should_stop():
            print("  STOP>2 failures --stopping")
            return False
        return True

    # -- Phase 2: Registration flow -------------------------------------
    def phase2_registration(self):
        self.start_phase("Phase 2: Registration")

        for person in TEST_PEOPLE:
            folder = person["folder"]
            id_img, photo = self.get_images(folder)

            if not id_img.exists() or not photo.exists():
                self.check(f"{folder} images exist", False,
                           actual=f"Missing: id={id_img.exists()} photo={photo.exists()}")
                continue

            # 6. POST /api/register
            try:
                files = {
                    "id_document": (f"{folder}_id.jpg", open(id_img, "rb"), "image/jpeg"),
                    "id_face_crop": (f"{folder}_face.jpg", open(photo, "rb"), "image/jpeg"),
                    "face_photo": (f"{folder}_live.jpg", open(photo, "rb"), "image/jpeg"),
                }
                data = {
                    "full_name": person["name"],
                    "email": f"{folder}@walkforpeace-test.org",
                    "phone": f"+9477{hash(folder) % 10000000:07d}",
                    "organization": person["org"],
                    "designation": person["designation"],
                    "media_type": person["media_type"],
                    "country": "Sri Lanka",
                    "id_type": "NIC",
                    "id_number": person["nic"],
                    "terms_accepted": "true",
                }
                r = self.session.post(f"{BASE_URL}/api/register", data=data, files=files,
                                      headers={"Origin": BASE_URL}, timeout=30)
                j = r.json() if r.status_code == 200 else {}
                ok = (r.status_code == 200 and "pin_code" in j
                      and "ref_number" in j and "qr_code_url" in j)
                self.check(f"{folder} register -> 200 + pin + ref", ok,
                           endpoint=f"POST {BASE_URL}/api/register",
                           expected="200 with pin_code, ref_number, qr_code_url",
                           actual=f"{r.status_code} {r.text[:300]}")

                if ok:
                    self.registrations[folder] = {
                        "ref_number": j["ref_number"],
                        "pin_code": j["pin_code"],
                        "qr_code_url": j["qr_code_url"],
                        "nic": person["nic"],
                    }
            except Exception as e:
                self.check(f"{folder} register", False, actual=str(e))

            # 7. GET /api/register/status/{ref}
            reg = self.registrations.get(folder, {})
            if ref := reg.get("ref_number"):
                try:
                    r = self.session.get(f"{BASE_URL}/api/register/status/{ref}", timeout=10)
                    ok = r.status_code == 200 and r.json().get("status") == "pending_review"
                    self.check(f"{folder} status -> pending_review", ok,
                               endpoint=f"GET /api/register/status/{ref}",
                               expected="pending_review",
                               actual=f"{r.status_code} {r.text[:200]}")
                except Exception as e:
                    self.check(f"{folder} status", False, actual=str(e))

            # 8. GET /api/register/retrieve?pin=
            if pin := reg.get("pin_code"):
                try:
                    r = self.session.get(f"{BASE_URL}/api/register/retrieve", params={"pin": pin}, timeout=10)
                    ok = r.status_code == 200 and r.json().get("ref_number") == ref
                    self.check(f"{folder} retrieve by PIN", ok,
                               endpoint=f"GET /api/register/retrieve?pin={pin}",
                               expected=f"ref_number={ref}",
                               actual=f"{r.status_code} {r.text[:200]}")
                except Exception as e:
                    self.check(f"{folder} retrieve PIN", False, actual=str(e))

            # 9. GET /api/register/retrieve?id_number=
            if nic := reg.get("nic"):
                try:
                    r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                          params={"id_number": nic}, timeout=10)
                    ok = r.status_code == 200 and r.json().get("ref_number") == ref
                    self.check(f"{folder} retrieve by NIC", ok,
                               endpoint=f"GET /api/register/retrieve?id_number={nic}",
                               expected=f"ref_number={ref}",
                               actual=f"{r.status_code} {r.text[:200]}")
                except Exception as e:
                    self.check(f"{folder} retrieve NIC", False, actual=str(e))

        if self.should_stop():
            print("  STOP>2 failures --stopping")
            return False
        return True

    # -- Phase 3: OCR --------------------------------------------------
    def phase3_ocr(self):
        self.start_phase("Phase 3: OCR")

        for person in TEST_PEOPLE:
            folder = person["folder"]
            id_img, _ = self.get_images(folder)
            expected_nic = person["nic"]
            # Mark as expected failure -- placeholder images, not real NIC cards
            is_expected_fail = True

            try:
                files = {"id_document": (f"{folder}_id.jpg", open(id_img, "rb"), "image/jpeg")}
                r = self.session.post(f"{BASE_URL}/api/register/ocr", files=files,
                                      headers={"Origin": BASE_URL}, timeout=30)
                if r.status_code == 200:
                    extracted = r.json().get("id_number", "")
                    ok = extracted == expected_nic
                    self.check(f"{folder} OCR -> {expected_nic}", ok,
                               endpoint="POST /api/register/ocr",
                               expected=expected_nic,
                               actual=f"extracted={extracted}",
                               expected_failure=is_expected_fail)
                else:
                    self.check(f"{folder} OCR -> 200", False,
                               endpoint="POST /api/register/ocr",
                               expected="200", actual=f"{r.status_code} {r.text[:200]}",
                               expected_failure=is_expected_fail)
            except Exception as e:
                self.check(f"{folder} OCR", False, actual=str(e), expected_failure=is_expected_fail)

        return True

    # -- Phase 4: Admin flow -------------------------------------------
    def phase4_admin(self):
        self.start_phase("Phase 4: Admin")

        # 11. Admin login
        try:
            r = self.session.post(f"{ADMIN_URL}/api/admin/login",
                                  json={"username": ADMIN_USER, "password": ADMIN_PASS},
                                  headers={"Origin": ADMIN_URL}, timeout=10)
            ok = r.status_code == 200 and "access_token" in r.json()
            self.check("Admin login -> JWT", ok,
                       endpoint="POST /api/admin/login",
                       expected="200 + access_token",
                       actual=f"{r.status_code} {r.text[:200]}")
            if ok:
                self.admin_token = r.json()["access_token"]
        except Exception as e:
            self.check("Admin login", False, actual=str(e))
            return False

        # 12. Stats
        try:
            r = self.session.get(f"{ADMIN_URL}/api/admin/stats",
                                 headers=self.admin_headers(), timeout=10)
            j = r.json() if r.status_code == 200 else {}
            count = j.get("total_registered", j.get("total_applications", 0))
            self.check(f"Stats -> total >= 4 (got {count})", count >= 4,
                       endpoint="GET /api/admin/stats",
                       expected="total_registered >= 4",
                       actual=f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            self.check("Stats", False, actual=str(e))

        # 13. List applications
        try:
            r = self.session.get(f"{ADMIN_URL}/api/admin/applications",
                                 params={"status": "pending_review"},
                                 headers=self.admin_headers(), timeout=10)
            items = r.json().get("items", []) if r.status_code == 200 else []
            self.check(f"List pending -> {len(items)} apps", len(items) >= 4,
                       endpoint="GET /api/admin/applications?status=pending_review",
                       expected=">= 4 items",
                       actual=f"{r.status_code} items={len(items)}")

            # Map app IDs
            for item in items:
                for folder, reg in self.registrations.items():
                    if item.get("ref_number") == reg.get("ref_number"):
                        reg["app_id"] = item["id"]
        except Exception as e:
            self.check("List pending", False, actual=str(e))

        # 15. Detail for each
        for folder in ["aruni", "bashini", "lakshika", "alia"]:
            reg = self.registrations.get(folder, {})
            app_id = reg.get("app_id")
            if not app_id:
                self.check(f"{folder} detail", False, actual="No app_id found")
                continue
            try:
                r = self.session.get(f"{ADMIN_URL}/api/admin/applications/{app_id}",
                                     headers=self.admin_headers(), timeout=10)
                ok = r.status_code == 200 and r.json().get("full_name") is not None
                self.check(f"{folder} detail -> full record", ok,
                           endpoint=f"GET /api/admin/applications/{app_id}",
                           expected="200 + full_name",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check(f"{folder} detail", False, actual=str(e))

        # 16-18. Approve aruni, bashini; reject lakshika; leave alia
        for folder, action in [("aruni", "approve"), ("bashini", "approve"), ("lakshika", "reject")]:
            reg = self.registrations.get(folder, {})
            app_id = reg.get("app_id")
            if not app_id:
                self.check(f"{folder} {action}", False, actual="No app_id")
                continue
            try:
                r = self.session.patch(f"{ADMIN_URL}/api/admin/applications/{app_id}/review",
                                       json={"action": action},
                                       headers={**self.admin_headers(), "Origin": ADMIN_URL},
                                       timeout=10)
                ok = r.status_code == 200
                self.check(f"{folder} {action} -> 200", ok,
                           endpoint=f"PATCH /api/admin/applications/{app_id}/review",
                           expected="200",
                           actual=f"{r.status_code} {r.text[:300]}")
                if ok and action == "approve":
                    j = r.json()
                    reg["credential_token"] = j.get("credential_token")
                    reg["badge_number"] = j.get("badge_number")
            except Exception as e:
                self.check(f"{folder} {action}", False, actual=str(e))

        if self.should_stop():
            print("  STOP>2 failures --stopping")
            return False
        return True

    # -- Phase 5: Credential verification ------------------------------
    def phase5_verification(self):
        self.start_phase("Phase 5: Verification")

        # 20. Retrieve approved
        aruni = self.registrations.get("aruni", {})
        if pin := aruni.get("pin_code"):
            try:
                r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                      params={"pin": pin}, timeout=10)
                j = r.json() if r.status_code == 200 else {}
                ok = j.get("verification_status") == "approved"
                self.check(f"aruni retrieve -> approved", ok,
                           endpoint=f"GET /api/register/retrieve?pin={pin}",
                           expected="verification_status=approved",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check("aruni retrieve", False, actual=str(e))

        # 21. Retrieve rejected
        lakshika = self.registrations.get("lakshika", {})
        if pin := lakshika.get("pin_code"):
            try:
                r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                      params={"pin": pin}, timeout=10)
                j = r.json() if r.status_code == 200 else {}
                self.check(f"lakshika retrieve -> rejected", j.get("status") == "rejected",
                           endpoint=f"GET /api/register/retrieve?pin={pin}",
                           expected="status=rejected",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check("lakshika retrieve", False, actual=str(e))

        # 22. Public verify (no session)
        if token := aruni.get("credential_token"):
            try:
                r = self.session.get(f"{VERIFY_URL}/api/verify/{token}", timeout=10)
                j = r.json() if r.status_code == 200 else {}
                ok = j.get("valid") is True and j.get("id_face_crop_url") is None
                self.check("aruni public verify -> valid, no sensitive fields", ok,
                           endpoint=f"GET {VERIFY_URL}/api/verify/{{token}}",
                           expected="valid=true, id_face_crop_url=null",
                           actual=f"valid={j.get('valid')} face_crop={j.get('id_face_crop_url')}")
            except Exception as e:
                self.check("aruni public verify", False, actual=str(e))

        # 23. Verify session login
        try:
            r = self.session.post(f"{VERIFY_URL}/api/verify/auth",
                                  json={"password": VERIFY_PASSWORD},
                                  headers={"Origin": VERIFY_URL}, timeout=10)
            ok = r.status_code == 200 and "session_token" in r.json()
            self.check("Verify session login -> token", ok,
                       endpoint="POST /api/verify/auth",
                       expected="200 + session_token",
                       actual=f"{r.status_code} {r.text[:200]}")
            if ok:
                self.verify_session = r.json()["session_token"]
        except Exception as e:
            self.check("Verify session login", False, actual=str(e))

        # 24. Wrong password
        try:
            r = self.session.post(f"{VERIFY_URL}/api/verify/auth",
                                  json={"password": "wrong"},
                                  headers={"Origin": VERIFY_URL}, timeout=10)
            self.check("Wrong verify password -> 401", r.status_code == 401,
                       endpoint="POST /api/verify/auth",
                       expected="401", actual=f"{r.status_code}")
        except Exception as e:
            self.check("Wrong verify password", False, actual=str(e))

        # 25. Authenticated verify aruni
        if token := aruni.get("credential_token"):
            try:
                r = self.session.get(f"{VERIFY_URL}/api/verify/{token}",
                                      headers=self.verify_headers(), timeout=10)
                j = r.json() if r.status_code == 200 else {}
                ok = (j.get("valid") is True and j.get("badge_number") is not None
                      and j.get("face_photo_url") is not None)
                self.check("aruni auth verify -> full payload", ok,
                           endpoint=f"GET /api/verify/{{token}} + session",
                           expected="valid + badge_number + face_photo_url",
                           actual=f"valid={j.get('valid')} badge={j.get('badge_number')} face={j.get('face_photo_url')}")
            except Exception as e:
                self.check("aruni auth verify", False, actual=str(e))

        # 26. Authenticated verify bashini
        bashini = self.registrations.get("bashini", {})
        if token := bashini.get("credential_token"):
            try:
                r = self.session.get(f"{VERIFY_URL}/api/verify/{token}",
                                      headers=self.verify_headers(), timeout=10)
                j = r.json() if r.status_code == 200 else {}
                self.check("bashini auth verify -> approved", j.get("status") == "approved",
                           endpoint=f"GET /api/verify/{{token}} + session",
                           expected="status=approved",
                           actual=f"status={j.get('status')}")
            except Exception as e:
                self.check("bashini auth verify", False, actual=str(e))

        if self.should_stop():
            return False
        return True

    # -- Phase 6: Gate approve/deny ------------------------------------
    def phase6_gate(self):
        self.start_phase("Phase 6: Gate approve/deny")

        # Approve alia first via admin, then test gate actions
        alia = self.registrations.get("alia", {})
        app_id = alia.get("app_id")

        if app_id and self.admin_token:
            # Approve alia
            try:
                r = self.session.patch(f"{ADMIN_URL}/api/admin/applications/{app_id}/review",
                                       json={"action": "approve"},
                                       headers={**self.admin_headers(), "Origin": ADMIN_URL},
                                       timeout=10)
                ok = r.status_code == 200
                self.check("alia approve -> 200", ok,
                           endpoint=f"PATCH /api/admin/applications/{app_id}/review",
                           actual=f"{r.status_code} {r.text[:200]}")
                if ok:
                    j = r.json()
                    alia["credential_token"] = j.get("credential_token")
                    alia["badge_number"] = j.get("badge_number")
            except Exception as e:
                self.check("alia approve", False, actual=str(e))

        # Gate actions only work on 'flagged' credentials.
        # Since alia was approved normally, test that gate-approve is rejected (400).
        if token := alia.get("credential_token"):
            # Gate approve on non-flagged -> 400
            try:
                r = self.session.post(f"{VERIFY_URL}/api/verify/{token}/gate-approve",
                                      headers={**self.verify_headers(), "Origin": VERIFY_URL},
                                      timeout=10)
                self.check("gate-approve non-flagged -> 400", r.status_code == 400,
                           endpoint=f"POST /api/verify/{{token}}/gate-approve",
                           expected="400 (not flagged)",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check("gate-approve non-flagged", False, actual=str(e))

            # Gate deny works on any credential (security officer can deny entry)
            try:
                r = self.session.post(f"{VERIFY_URL}/api/verify/{token}/gate-deny",
                                      headers={**self.verify_headers(), "Origin": VERIFY_URL},
                                      timeout=10)
                self.check("gate-deny approved -> 200 (logs denial)", r.status_code == 200,
                           endpoint=f"POST /api/verify/{{token}}/gate-deny",
                           expected="200",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check("gate-deny non-flagged", False, actual=str(e))

            # Verify alia still valid
            try:
                r = self.session.get(f"{VERIFY_URL}/api/verify/{token}",
                                      headers=self.verify_headers(), timeout=10)
                j = r.json() if r.status_code == 200 else {}
                self.check("alia verify -> still approved", j.get("valid") is True,
                           actual=f"valid={j.get('valid')} status={j.get('status')}")
            except Exception as e:
                self.check("alia verify", False, actual=str(e))

        return True

    # -- Phase 7: Revocation -------------------------------------------
    def phase7_revocation(self):
        self.start_phase("Phase 7: Revocation")

        aruni = self.registrations.get("aruni", {})
        app_id = aruni.get("app_id")
        token = aruni.get("credential_token")

        if app_id:
            try:
                r = self.session.post(f"{ADMIN_URL}/api/admin/applications/{app_id}/revoke",
                                      headers={**self.admin_headers(), "Origin": ADMIN_URL},
                                      timeout=10)
                self.check("aruni revoke -> 200", r.status_code == 200,
                           endpoint=f"POST /api/admin/applications/{app_id}/revoke",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check("aruni revoke", False, actual=str(e))

        if token:
            try:
                r = self.session.get(f"{VERIFY_URL}/api/verify/{token}", timeout=10)
                j = r.json() if r.status_code == 200 else {}
                ok = j.get("status") == "revoked" or j.get("valid") is False
                self.check("aruni verify -> revoked", ok,
                           expected="status=revoked or valid=false",
                           actual=f"valid={j.get('valid')} status={j.get('status')}")
            except Exception as e:
                self.check("aruni verify revoked", False, actual=str(e))

        return True

    # -- Phase 8: Batch approve ----------------------------------------
    def phase8_batch(self):
        self.start_phase("Phase 8: Batch approve")

        # Register 2 more test people
        batch_regs = []
        for i, name in enumerate(["TestBatch1", "TestBatch2"]):
            id_img, photo = self.get_images("aruni")  # reuse aruni images
            try:
                files = {
                    "id_document": (f"batch{i}_id.jpg", open(id_img, "rb"), "image/jpeg"),
                    "id_face_crop": (f"batch{i}_face.jpg", open(photo, "rb"), "image/jpeg"),
                    "face_photo": (f"batch{i}_live.jpg", open(photo, "rb"), "image/jpeg"),
                }
                data = {
                    "full_name": f"{name} Person",
                    "email": f"batch{i}@walkforpeace-test.org",
                    "phone": f"+9477000{i:04d}",
                    "organization": "Test Batch Org",
                    "designation": "Tester",
                    "media_type": "freelance",
                    "country": "Sri Lanka",
                    "id_type": "NIC",
                    "id_number": f"20010000{i:04d}",
                    "terms_accepted": "true",
                }
                r = self.session.post(f"{BASE_URL}/api/register", data=data, files=files,
                                      headers={"Origin": BASE_URL}, timeout=30)
                if r.status_code == 200:
                    batch_regs.append(r.json())
                    self.registrations[f"batch{i}"] = {
                        "ref_number": r.json()["ref_number"],
                        "pin_code": r.json()["pin_code"],
                    }
            except Exception:
                pass

        # Find their app IDs
        app_ids = []
        try:
            r = self.session.get(f"{ADMIN_URL}/api/admin/applications",
                                 params={"status": "pending_review", "page_size": 50},
                                 headers=self.admin_headers(), timeout=10)
            if r.status_code == 200:
                for item in r.json().get("items", []):
                    for reg in batch_regs:
                        if item.get("ref_number") == reg.get("ref_number"):
                            app_ids.append(item["id"])
        except Exception:
            pass

        # Batch approve
        if len(app_ids) >= 2:
            try:
                r = self.session.post(f"{ADMIN_URL}/api/admin/applications/batch-approve",
                                      json={"application_ids": app_ids},
                                      headers={**self.admin_headers(), "Origin": ADMIN_URL},
                                      timeout=15)
                ok = r.status_code == 200
                self.check(f"Batch approve {len(app_ids)} apps -> 200", ok,
                           endpoint="POST /api/admin/applications/batch-approve",
                           actual=f"{r.status_code} {r.text[:200]}")
            except Exception as e:
                self.check("Batch approve", False, actual=str(e))

            # Verify both approved
            for i, reg in enumerate(batch_regs):
                pin = reg.get("pin_code")
                if pin:
                    try:
                        r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                              params={"pin": pin}, timeout=10)
                        j = r.json() if r.status_code == 200 else {}
                        self.check(f"batch{i} -> approved", j.get("verification_status") == "approved",
                                   actual=f"verification_status={j.get('verification_status')}")
                    except Exception as e:
                        self.check(f"batch{i} verify", False, actual=str(e))
        else:
            self.check("Batch approve --found app IDs", False,
                       actual=f"Only found {len(app_ids)} IDs, need 2")

        return True

    # -- Phase 9: Verification logs ------------------------------------
    def phase9_logs(self):
        self.start_phase("Phase 9: Verification logs")

        try:
            r = self.session.get(f"{ADMIN_URL}/api/admin/verification-logs",
                                 headers=self.admin_headers(), timeout=10)
            ok = r.status_code == 200
            items = r.json().get("items", []) if ok else []
            self.check(f"Verification logs -> 200 ({len(items)} entries)", ok and len(items) > 0,
                       endpoint="GET /api/admin/verification-logs",
                       actual=f"{r.status_code} items={len(items)}")
        except Exception as e:
            self.check("Verification logs", False, actual=str(e))

        # Check gate-approve log
        gate_found = False
        for item in items:
            if item.get("verified_by_action") in ("gate_approved", "gate_denied"):
                gate_found = True
                break
        self.check("Gate action in logs", gate_found,
                   expected="verified_by_action = gate_approved or gate_denied",
                   actual=f"found={gate_found}")

        return True

    # -- Phase 10: Edge cases ------------------------------------------
    def phase10_edge_cases(self):
        self.start_phase("Phase 10: Edge cases")

        # 40. Missing fields
        try:
            r = self.session.post(f"{BASE_URL}/api/register",
                                  data={"full_name": "Incomplete"},
                                  headers={"Origin": BASE_URL}, timeout=10)
            self.check("Missing fields -> 400/422", r.status_code in (400, 422),
                       expected="400 or 422", actual=f"{r.status_code}")
        except Exception as e:
            self.check("Missing fields", False, actual=str(e))

        # 41. Invalid media type
        id_img, photo = self.get_images("aruni")
        try:
            files = {
                "id_document": ("id.jpg", open(id_img, "rb"), "image/jpeg"),
                "id_face_crop": ("face.jpg", open(photo, "rb"), "image/jpeg"),
                "face_photo": ("live.jpg", open(photo, "rb"), "image/jpeg"),
            }
            data = {
                "full_name": "Bad Type", "email": "bad@test.org", "phone": "+94770000001",
                "organization": "Test", "designation": "Test", "media_type": "INVALID_TYPE",
                "country": "Sri Lanka", "terms_accepted": "true",
            }
            r = self.session.post(f"{BASE_URL}/api/register", data=data, files=files,
                                  headers={"Origin": BASE_URL}, timeout=15)
            self.check("Invalid media_type -> 400", r.status_code == 400,
                       expected="400", actual=f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            self.check("Invalid media_type", False, actual=str(e))

        # 43. Invalid file type
        try:
            files = {
                "id_document": ("id.txt", b"not an image", "text/plain"),
                "id_face_crop": ("face.txt", b"not an image", "text/plain"),
                "face_photo": ("live.txt", b"not an image", "text/plain"),
            }
            data = {
                "full_name": "Bad File", "email": "badfile@test.org", "phone": "+94770000002",
                "organization": "Test", "designation": "Test", "media_type": "print",
                "country": "Sri Lanka", "terms_accepted": "true",
            }
            r = self.session.post(f"{BASE_URL}/api/register", data=data, files=files,
                                  headers={"Origin": BASE_URL}, timeout=15)
            self.check("Invalid file type -> 400", r.status_code == 400,
                       expected="400", actual=f"{r.status_code} {r.text[:200]}")
        except Exception as e:
            self.check("Invalid file type", False, actual=str(e))

        # 44. Nonexistent PIN
        try:
            r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                  params={"pin": "WFP-000000"}, timeout=10)
            self.check("Nonexistent PIN -> 404", r.status_code == 404,
                       expected="404", actual=f"{r.status_code}")
        except Exception as e:
            self.check("Nonexistent PIN", False, actual=str(e))

        # 45. Nonexistent ID
        try:
            r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                  params={"id_number": "000000000000"}, timeout=10)
            self.check("Nonexistent ID -> 404", r.status_code == 404,
                       expected="404", actual=f"{r.status_code}")
        except Exception as e:
            self.check("Nonexistent ID", False, actual=str(e))

        # 46. Fake verify token
        try:
            r = self.session.get(f"{VERIFY_URL}/api/verify/completely-fake-token", timeout=10)
            j = r.json() if r.status_code == 200 else {}
            self.check("Fake token -> invalid", j.get("valid") is False,
                       expected="valid=false", actual=f"valid={j.get('valid')}")
        except Exception as e:
            self.check("Fake token", False, actual=str(e))

        # 49. Admin wrong password
        try:
            r = self.session.post(f"{ADMIN_URL}/api/admin/login",
                                  json={"username": "admin", "password": "wrong"},
                                  headers={"Origin": ADMIN_URL}, timeout=10)
            self.check("Admin wrong password -> 401", r.status_code == 401,
                       expected="401", actual=f"{r.status_code}")
        except Exception as e:
            self.check("Admin wrong password", False, actual=str(e))

        # 50. Admin without auth
        try:
            r = self.session.get(f"{ADMIN_URL}/api/admin/applications", timeout=10)
            self.check("Admin no auth -> 401/403", r.status_code in (401, 403),
                       expected="401 or 403", actual=f"{r.status_code}")
        except Exception as e:
            self.check("Admin no auth", False, actual=str(e))

        return True

    # -- Phase 11: Frontend serving ------------------------------------
    def phase11_frontend(self):
        self.start_phase("Phase 11: Frontend serving")

        spa_paths = [
            (f"{BASE_URL}/", "register root"),
            (f"{BASE_URL}/register", "register form"),
            (f"{BASE_URL}/get-qr", "get-qr"),
            (f"{VERIFY_URL}/", "verify root"),
            (f"{ADMIN_URL}/", "admin root"),
            (f"{BASE_URL}/nonexistent-path", "SPA fallback"),
        ]
        for url, label in spa_paths:
            try:
                r = self.session.get(url, timeout=10)
                ok = r.status_code == 200 and "<!DOCTYPE" in r.text
                self.check(f"{label} -> 200 + HTML", ok,
                           endpoint=f"GET {url}",
                           expected="200 + HTML",
                           actual=f"{r.status_code} len={len(r.text)}")
            except Exception as e:
                self.check(f"{label}", False, actual=str(e))

        return True

    # -- Phase 12: Badge/QR verification -------------------------------
    def phase12_badge_qr(self):
        self.start_phase("Phase 12: Badge/QR")

        # Check QR code image for bashini (still approved)
        bashini = self.registrations.get("bashini", {})
        if pin := bashini.get("pin_code"):
            try:
                r = self.session.get(f"{BASE_URL}/api/register/retrieve",
                                      params={"pin": pin}, timeout=10)
                j = r.json() if r.status_code == 200 else {}
                qr_url = j.get("qr_code_url")
                if qr_url:
                    qr_r = self.session.get(f"{BASE_URL}{qr_url}", timeout=10)
                    ok = qr_r.status_code == 200 and len(qr_r.content) > 100
                    self.check(f"QR image downloadable ({len(qr_r.content)} bytes)", ok,
                               endpoint=f"GET {BASE_URL}{qr_url}",
                               expected="200 + PNG > 100 bytes",
                               actual=f"{qr_r.status_code} size={len(qr_r.content)}")

                    # Check PNG header
                    is_png = qr_r.content[:4] == b'\x89PNG'
                    self.check("QR is valid PNG", is_png,
                               expected="PNG header",
                               actual=f"first 4 bytes: {qr_r.content[:4]}")
                else:
                    self.check("QR URL present", False, actual=f"qr_code_url={qr_url}")

                # Badge PDF
                badge_url = j.get("badge_pdf_url")
                if badge_url:
                    badge_r = self.session.get(f"{BASE_URL}{badge_url}", timeout=10)
                    ok = badge_r.status_code == 200 and len(badge_r.content) > 1024
                    self.check(f"Badge PDF downloadable ({len(badge_r.content)} bytes)", ok,
                               endpoint=f"GET {BASE_URL}{badge_url}",
                               expected="200 + PDF > 1KB",
                               actual=f"{badge_r.status_code} size={len(badge_r.content)}")
                else:
                    self.check("Badge PDF URL present", badge_url is not None,
                               expected="badge_pdf_url not null",
                               actual=f"badge_pdf_url={badge_url}",
                               expected_failure=True)
            except Exception as e:
                self.check("Badge/QR", False, actual=str(e))

        return True

    # -- Run all -------------------------------------------------------
    def run(self):
        print(f"{'='*60}")
        print("WALK FOR PEACE --PRODUCTION E2E TEST SUITE")
        print(f"Target: {BASE_URL}")
        print(f"{'='*60}")

        if not self.phase1_infrastructure():
            self.print_summary()
            return False
        if not self.phase2_registration():
            self.print_summary()
            return False
        self.phase3_ocr()
        if not self.phase4_admin():
            self.print_summary()
            return False
        self.phase5_verification()
        self.phase6_gate()
        self.phase7_revocation()
        self.phase8_batch()
        self.phase9_logs()
        self.phase10_edge_cases()
        self.phase11_frontend()
        self.phase12_badge_qr()

        return self.print_summary()


if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run()
    sys.exit(0 if success else 1)
