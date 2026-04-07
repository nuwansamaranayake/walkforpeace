#!/bin/bash
# Walk for Peace — Post-deploy smoke test
# Verifies all critical endpoints return real data
set -e

BASE_URL="${1:-http://localhost}"
PASS=0
FAIL=0

check() {
  local desc="$1" url="$2" expect="$3"
  response=$(curl -s -o /tmp/smoke_body -w "%{http_code}" "$url" 2>/dev/null)
  body=$(cat /tmp/smoke_body)

  if [[ "$response" == "$expect" ]]; then
    echo "✅ $desc (HTTP $response)"
    ((PASS++))
  else
    echo "❌ $desc — expected HTTP $expect, got $response"
    echo "   Body: $(echo "$body" | head -c 200)"
    ((FAIL++))
  fi
}

check_json() {
  local desc="$1" url="$2" field="$3"
  response=$(curl -s "$url" 2>/dev/null)

  if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null; then
    echo "✅ $desc (field '$field' present)"
    ((PASS++))
  else
    echo "❌ $desc — field '$field' missing in response"
    echo "   Body: $(echo "$response" | head -c 200)"
    ((FAIL++))
  fi
}

echo "🔍 Walk for Peace — Smoke Test"
echo "   Target: $BASE_URL"
echo "---"

# Health check
check_json "API health" "$BASE_URL/api/health" "status"

# Registration endpoint exists (GET should 405, POST expected)
check "Registration endpoint" "$BASE_URL/api/register" "405"

# Status check with fake ref (should 404)
check "Status check (not found)" "$BASE_URL/api/register/status/FAKE-REF" "404"

# Admin login endpoint exists
check "Admin login endpoint" "$BASE_URL/api/admin/login" "405"

# Stats requires auth (should 403 or 401)
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/admin/stats")
if [[ "$response" == "401" || "$response" == "403" ]]; then
  echo "✅ Admin stats requires auth (HTTP $response)"
  ((PASS++))
else
  echo "❌ Admin stats — expected 401/403, got $response"
  ((FAIL++))
fi

# Verify endpoint with fake token
check "Verify fake token" "$BASE_URL/api/verify/fake-token" "200"

# Frontend serves
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/")
if [[ "$response" == "200" ]]; then
  echo "✅ Frontend serves (HTTP 200)"
  ((PASS++))
else
  echo "❌ Frontend — expected HTTP 200, got $response"
  ((FAIL++))
fi

# Admin login and test authenticated endpoint
echo "---"
echo "🔐 Testing admin auth flow..."
LOGIN_RESP=$(curl -s -X POST "$BASE_URL/api/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"WalkForPeace2026!"}')

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [[ -n "$TOKEN" && "$TOKEN" != "" ]]; then
  echo "✅ Admin login successful"
  ((PASS++))

  # Test stats with token
  STATS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/admin/stats")
  if echo "$STATS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'total_registered' in d" 2>/dev/null; then
    echo "✅ Admin stats returns data"
    ((PASS++))
  else
    echo "❌ Admin stats — no data returned"
    ((FAIL++))
  fi

  # Test applications list
  APPS=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/admin/applications?page=1&page_size=5")
  if echo "$APPS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'items' in d" 2>/dev/null; then
    echo "✅ Admin applications list returns data"
    ((PASS++))
  else
    echo "❌ Admin applications list — no data"
    ((FAIL++))
  fi
else
  echo "❌ Admin login failed"
  echo "   Response: $(echo "$LOGIN_RESP" | head -c 200)"
  ((FAIL++))
fi

# Database table verification
echo "---"
echo "🗄️  Verifying database tables..."
EXPECTED_TABLES=("media_applications" "credentials" "admin_users" "verification_logs")
DB_URL="${DATABASE_URL:-postgresql://walkforpeace:walkforpeace@localhost:5432/walkforpeace}"

for table in "${EXPECTED_TABLES[@]}"; do
  if PGPASSWORD=walkforpeace psql -h localhost -U walkforpeace -d walkforpeace -tc "SELECT 1 FROM information_schema.tables WHERE table_name='$table'" 2>/dev/null | grep -q 1; then
    echo "✅ Table '$table' exists"
    ((PASS++))
  else
    echo "❌ Table '$table' MISSING"
    ((FAIL++))
  fi
done

echo "---"
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && echo "🎉 All smoke tests passed!" || echo "⚠️  Some tests failed!"
exit $FAIL
