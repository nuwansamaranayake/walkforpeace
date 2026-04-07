"""Integration tests for Walk for Peace API — automates the proven E2E curl flow."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, test_images, name="Test User", email="test@example.com"):
    """Helper: register a media person and return ref_number."""
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
    }
    resp = await client.post('/api/register', data=data, files=files)
    return resp


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
        resp = await _register(client, test_images, "Reg Test", "reg@test.com")
        assert resp.status_code == 200
        body = resp.json()
        assert body['ref_number'].startswith('WFP-')
        assert body['status'] == 'pending_review'
        assert 'submitted' in body['message'].lower() or 'success' in body['message'].lower()

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
        assert vbody['status'] == 'valid'
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
