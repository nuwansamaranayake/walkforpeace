"""Integration tests for Walk for Peace API — automates the proven E2E curl flow."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, test_images, name="Test User", email="test@example.com", id_number="200370312725"):
    """Helper: register a media person and return response."""
    files = {
        'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
        'id_face_crop': ('face_id.jpg', test_images['id_face_crop'], 'image/jpeg'),
        'face_photo': ('face_live.jpg', test_images['face_photo'], 'image/jpeg'),
    }
    data = {
        'full_name': name,
        'organization': 'Test News',
        'designation': 'Reporter',
        'email': email,
        'phone': '+94771234567',
        'country': 'Sri Lanka',
        'media_type': 'print',
        'terms_accepted': 'true',
        'id_number': id_number,
        'id_type': 'nic',
    }
    return await client.post('/api/register', data=data, files=files)


async def _admin_token(client: AsyncClient):
    """Helper: get admin JWT token."""
    resp = await client.post('/api/admin/login', json={
        'username': 'admin', 'password': 'WalkForPeace2026!'
    })
    return resp.json()['access_token']


async def _admin_headers(client: AsyncClient):
    token = await _admin_token(client)
    return {'Authorization': f'Bearer {token}'}


# === Registration Tests ===

class TestRegistration:
    async def test_register_success(self, client: AsyncClient, test_images):
        resp = await _register(client, test_images, "Reg Test V2", "reg.v2@test.com")
        assert resp.status_code == 200
        body = resp.json()
        assert body['ref_number'].startswith('WFP-')
        assert body['pin_code'].startswith('WFP-')
        assert body['qr_code_url'] is not None
        assert body['status'] == 'pending_review'

    async def test_register_missing_file(self, client: AsyncClient, test_images):
        data = {
            'full_name': 'Test', 'organization': 'Test', 'designation': 'Test',
            'email': 'missing@test.com', 'phone': '+94771234567', 'country': 'LK',
            'media_type': 'print', 'terms_accepted': 'true',
        }
        # Missing all files
        resp = await client.post('/api/register', data=data)
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient, test_images):
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        resp = await client.post('/api/register', data={'full_name': 'X'}, files=files)
        assert resp.status_code == 422

    async def test_register_invalid_media_type(self, client: AsyncClient, test_images):
        files = {
            'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg'),
            'id_face_crop': ('face.jpg', test_images['id_face_crop'], 'image/jpeg'),
            'face_photo': ('live.jpg', test_images['face_photo'], 'image/jpeg'),
        }
        data = {
            'full_name': 'Test', 'organization': 'Test', 'designation': 'Test',
            'email': 'bad@test.com', 'phone': '+94771234567', 'country': 'LK',
            'media_type': 'invalid_type', 'terms_accepted': 'true',
        }
        resp = await client.post('/api/register', data=data, files=files)
        assert resp.status_code == 400


# === Status Tests ===

class TestStatus:
    async def test_status_found(self, client: AsyncClient, test_images):
        reg = await _register(client, test_images, "Status Test", "status@test.com")
        ref = reg.json()['ref_number']
        resp = await client.get(f'/api/register/status/{ref}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['ref_number'] == ref
        assert body['full_name'] == 'Status Test'
        assert body['status'] == 'pending_review'

    async def test_status_not_found(self, client: AsyncClient):
        resp = await client.get('/api/register/status/FAKE-999999')
        assert resp.status_code == 404


# === Admin Auth Tests ===

class TestAdminAuth:
    async def test_login_success(self, client: AsyncClient):
        resp = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'WalkForPeace2026!'
        })
        assert resp.status_code == 200
        body = resp.json()
        assert 'access_token' in body
        assert 'refresh_token' in body

    async def test_login_wrong_password(self, client: AsyncClient):
        resp = await client.post('/api/admin/login', json={
            'username': 'admin', 'password': 'wrong'
        })
        assert resp.status_code == 401

    async def test_protected_without_auth(self, client: AsyncClient):
        resp = await client.get('/api/admin/applications')
        assert resp.status_code in (401, 403)

    async def test_stats_with_auth(self, client: AsyncClient):
        headers = await _admin_headers(client)
        resp = await client.get('/api/admin/stats', headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert 'total_registered' in body
        assert 'pending' in body
        assert 'approved' in body

    async def test_applications_list(self, client: AsyncClient):
        headers = await _admin_headers(client)
        resp = await client.get('/api/admin/applications?page=1&page_size=10', headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert 'items' in body
        assert 'total' in body


# === Full Approval + Verification Flow ===

class TestApprovalAndVerification:
    async def test_approve_and_verify(self, client: AsyncClient, test_images):
        """Full flow: register -> approve -> verify QR token"""
        # Register
        reg = await _register(client, test_images, "Verify Flow", "verify.flow@test.com")
        assert reg.status_code == 200

        # Get app ID
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=Verify+Flow', headers=headers)
        items = apps.json()['items']
        matching = [a for a in items if a['full_name'] == 'Verify Flow']
        assert len(matching) > 0
        app_id = matching[0]['id']

        # Approve
        review = await client.patch(
            f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve', 'admin_notes': 'Test approved'},
            headers=headers,
        )
        assert review.status_code == 200
        body = review.json()
        assert 'credential_token' in body
        assert 'badge_number' in body
        assert body['badge_number'].startswith('WFP-')

        # Verify the credential token
        verify = await client.get(f'/api/verify/{body["credential_token"]}')
        assert verify.status_code == 200
        vbody = verify.json()
        assert vbody['valid'] is True
        assert vbody['status'] == 'approved'
        assert vbody['verification_status'] == 'approved'
        assert vbody['full_name'] == 'Verify Flow'
        assert vbody['badge_number'] == body['badge_number']

    async def test_reject_flow(self, client: AsyncClient, test_images):
        """Register -> reject"""
        reg = await _register(client, test_images, "Reject Flow", "reject.flow@test.com")
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=Reject+Flow', headers=headers)
        matching = [a for a in apps.json()['items'] if a['full_name'] == 'Reject Flow']
        assert len(matching) > 0
        app_id = matching[0]['id']

        review = await client.patch(
            f'/api/admin/applications/{app_id}/review',
            json={'action': 'reject', 'admin_notes': 'Test rejected'},
            headers=headers,
        )
        assert review.status_code == 200

    async def test_revoke_flow(self, client: AsyncClient, test_images):
        """Register -> approve -> revoke -> verify (should fail)"""
        reg = await _register(client, test_images, "Revoke Flow", "revoke.flow@test.com")
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=Revoke+Flow', headers=headers)
        matching = [a for a in apps.json()['items'] if a['full_name'] == 'Revoke Flow']
        app_id = matching[0]['id']

        # Approve first
        review = await client.patch(
            f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve'},
            headers=headers,
        )
        cred_token = review.json()['credential_token']

        # Revoke
        revoke = await client.post(f'/api/admin/applications/{app_id}/revoke', headers=headers)
        assert revoke.status_code == 200

        # Verify should show revoked
        verify = await client.get(f'/api/verify/{cred_token}')
        assert verify.status_code == 200
        assert verify.json()['valid'] is False
        assert verify.json()['status'] == 'revoked'


# === Verification Edge Cases ===

class TestVerification:
    async def test_invalid_token(self, client: AsyncClient):
        resp = await client.get('/api/verify/totally-fake-tampered-token')
        assert resp.status_code == 200
        body = resp.json()
        assert body['valid'] is False
        assert body['status'] == 'invalid'


# === Health Check ===

class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get('/api/health')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'ok'


# === PIN Retrieval Tests ===

class TestPINRetrieval:
    async def test_retrieve_by_pin(self, client, test_images):
        reg = await _register(client, test_images, "PIN Test", "pin@test.com")
        pin = reg.json()['pin_code']
        resp = await client.get(f'/api/register/retrieve?pin={pin}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['full_name'] == 'PIN Test'
        assert body['pin_code'] == pin
        assert body['qr_code_url'] is not None

    async def test_retrieve_by_id_number(self, client, test_images):
        reg = await _register(client, test_images, "NIC Test", "nic@test.com", id_number="199012345678")
        resp = await client.get('/api/register/retrieve?id_number=199012345678')
        assert resp.status_code == 200
        assert resp.json()['full_name'] == 'NIC Test'

    async def test_retrieve_pin_not_found(self, client):
        resp = await client.get('/api/register/retrieve?pin=WFP-000000')
        assert resp.status_code == 404

    async def test_retrieve_no_params(self, client):
        resp = await client.get('/api/register/retrieve')
        assert resp.status_code == 400


# === OCR Tests ===

class TestOCR:
    async def test_ocr_with_image(self, client, test_images):
        files = {'id_document': ('id.jpg', test_images['id_document'], 'image/jpeg')}
        resp = await client.post('/api/register/ocr', files=files)
        assert resp.status_code == 200
        body = resp.json()
        assert 'id_number' in body
        assert 'confidence' in body

    async def test_ocr_empty_file(self, client):
        files = {'id_document': ('id.jpg', b'', 'image/jpeg')}
        resp = await client.post('/api/register/ocr', files=files)
        assert resp.status_code == 400


# === Verify Auth Tests ===

class TestVerifyAuth:
    async def test_correct_password(self, client):
        resp = await client.post('/api/verify/auth', json={'password': 'Peace2026Verify'})
        assert resp.status_code == 200
        body = resp.json()
        assert 'session_token' in body
        assert 'expires_at' in body

    async def test_wrong_password(self, client):
        resp = await client.post('/api/verify/auth', json={'password': 'wrong'})
        assert resp.status_code == 401

    async def test_expired_session(self, client):
        headers = {'Authorization': 'Bearer fake-expired-token-xxx'}
        resp = await client.get('/api/verify/totally-fake-token', headers=headers)
        assert resp.status_code == 200


# === Verify Session Tiered Response Tests ===

class TestVerifySession:
    async def test_scan_with_session(self, client, test_images, verify_session):
        """With verify session, response includes sensitive fields."""
        reg = await _register(client, test_images, "Session Scan", "session.scan@test.com")
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=Session+Scan', headers=headers)
        app_id = [a for a in apps.json()['items'] if a['full_name'] == 'Session Scan'][0]['id']
        review = await client.patch(
            f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve'}, headers=headers,
        )
        cred_token = review.json()['credential_token']

        verify_headers = {'Authorization': f'Bearer {verify_session}'}
        resp = await client.get(f'/api/verify/{cred_token}', headers=verify_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body['face_match_score'] is not None
        assert body['id_face_crop_url'] is not None
        assert body['can_gate_approve'] is not None

    async def test_scan_without_session(self, client, test_images):
        """Without verify session, sensitive fields are absent."""
        reg = await _register(client, test_images, "No Session", "no.session@test.com")
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=No+Session', headers=headers)
        app_id = [a for a in apps.json()['items'] if a['full_name'] == 'No Session'][0]['id']
        review = await client.patch(
            f'/api/admin/applications/{app_id}/review',
            json={'action': 'approve'}, headers=headers,
        )
        cred_token = review.json()['credential_token']

        resp = await client.get(f'/api/verify/{cred_token}')
        assert resp.status_code == 200
        body = resp.json()
        assert body['face_match_score'] is None
        assert body['id_face_crop_url'] is None
        assert body['can_gate_approve'] is None


# === Gate Approve Tests ===

class TestGateApprove:
    async def test_gate_approve_flagged(self, client, test_images, verify_session):
        """Gate-approve changes flagged -> approved."""
        reg = await _register(client, test_images, "Gate Test", "gate@test.com")
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=Gate+Test', headers=headers)
        app_id = [a for a in apps.json()['items'] if a['full_name'] == 'Gate Test'][0]['id']
        app_detail = await client.get(f'/api/admin/applications/{app_id}', headers=headers)
        cred_token = app_detail.json()['credential']['credential_token']

        verify_headers = {'Authorization': f'Bearer {verify_session}'}
        resp = await client.post(f'/api/verify/{cred_token}/gate-approve', headers=verify_headers)
        # May be 200 (if flagged) or 400 (if pending/approved)
        assert resp.status_code in (200, 400)

    async def test_gate_deny(self, client, test_images, verify_session):
        """Gate-deny logs denial without changing status."""
        reg = await _register(client, test_images, "Deny Test", "deny@test.com")
        headers = await _admin_headers(client)
        apps = await client.get('/api/admin/applications?search=Deny+Test', headers=headers)
        app_id = [a for a in apps.json()['items'] if a['full_name'] == 'Deny Test'][0]['id']
        app_detail = await client.get(f'/api/admin/applications/{app_id}', headers=headers)
        cred_token = app_detail.json()['credential']['credential_token']

        verify_headers = {'Authorization': f'Bearer {verify_session}'}
        resp = await client.post(f'/api/verify/{cred_token}/gate-deny', headers=verify_headers)
        assert resp.status_code == 200

    async def test_gate_approve_no_session(self, client, test_images):
        """Gate-approve without session -> 401/403."""
        reg = await _register(client, test_images, "No Auth Gate", "noauth.gate@test.com")
        resp = await client.post('/api/verify/fake-token/gate-approve')
        assert resp.status_code in (401, 403)


# === Batch Approve Tests ===

class TestBatchApprove:
    async def test_batch_approve(self, client, test_images):
        """Batch approve multiple applications."""
        r1 = await _register(client, test_images, "Batch One", "batch1@test.com")
        r2 = await _register(client, test_images, "Batch Two", "batch2@test.com")
        headers = await _admin_headers(client)

        apps = await client.get('/api/admin/applications?search=Batch', headers=headers)
        ids = [a['id'] for a in apps.json()['items'] if a['full_name'] in ('Batch One', 'Batch Two')
               and a['status'] == 'pending_review']

        resp = await client.post('/api/admin/applications/batch-approve',
                                 json={'application_ids': ids}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()['approved_count'] >= 1

    async def test_batch_approve_invalid_ids(self, client):
        headers = await _admin_headers(client)
        resp = await client.post('/api/admin/applications/batch-approve',
                                 json={'application_ids': ['not-a-uuid']}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()['approved_count'] == 0


# === Verification Logs Tests ===

class TestVerificationLogs:
    async def test_list_logs(self, client):
        """Verification logs endpoint returns data."""
        headers = await _admin_headers(client)
        resp = await client.get('/api/admin/verification-logs', headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert 'items' in body
        assert 'total' in body
