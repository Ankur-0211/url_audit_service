#!/usr/bin/env bash
# Post-deploy smoke test — hits a live URL and checks the two critical
# paths (health + a real audit). Exits non-zero on any failure so it can
# be wired into a deploy pipeline later if desired.
#
# Usage: ./scripts/smoke_test.sh https://your-service.onrender.com

set -euo pipefail

BASE_URL="${1:-}"

if [ -z "$BASE_URL" ]; then
  echo "Usage: $0 <base_url>"
  echo "Example: $0 https://url-audit-service.onrender.com"
  exit 1
fi

BASE_URL="${BASE_URL%/}"

echo "== Smoke testing $BASE_URL =="

echo "-- GET /health"
HEALTH_STATUS=$(curl -s -o /tmp/health_body.json -w "%{http_code}" "$BASE_URL/health")
cat /tmp/health_body.json
echo
if [ "$HEALTH_STATUS" != "200" ]; then
  echo "FAIL: /health returned $HEALTH_STATUS"
  exit 1
fi
echo "OK: /health returned 200"
echo

echo "-- GET /"
ROOT_STATUS=$(curl -s -o /tmp/root_body.json -w "%{http_code}" "$BASE_URL/")
cat /tmp/root_body.json
echo
if [ "$ROOT_STATUS" != "200" ]; then
  echo "FAIL: / returned $ROOT_STATUS"
  exit 1
fi
echo "OK: / returned 200"
echo

echo "-- POST /audit (happy path: https://example.com)"
AUDIT_STATUS=$(curl -s -o /tmp/audit_body.json -w "%{http_code}" \
  -X POST "$BASE_URL/audit" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}')
cat /tmp/audit_body.json
echo
if [ "$AUDIT_STATUS" != "200" ]; then
  echo "FAIL: /audit happy path returned $AUDIT_STATUS"
  exit 1
fi
echo "OK: /audit happy path returned 200"
echo

echo "-- POST /audit (SSRF guard: http://localhost/)"
SSRF_STATUS=$(curl -s -o /tmp/ssrf_body.json -w "%{http_code}" \
  -X POST "$BASE_URL/audit" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost/"}')
cat /tmp/ssrf_body.json
echo
if [ "$SSRF_STATUS" != "403" ]; then
  echo "FAIL: /audit SSRF guard expected 403, got $SSRF_STATUS"
  exit 1
fi
echo "OK: /audit correctly blocked localhost with 403"
echo

echo "-- POST /audit (validation error: bad URL)"
VALIDATION_STATUS=$(curl -s -o /tmp/validation_body.json -w "%{http_code}" \
  -X POST "$BASE_URL/audit" \
  -H "Content-Type: application/json" \
  -d '{"url": "not-a-url"}')
cat /tmp/validation_body.json
echo
if [ "$VALIDATION_STATUS" != "422" ]; then
  echo "FAIL: /audit validation expected 422, got $VALIDATION_STATUS"
  exit 1
fi
echo "OK: /audit correctly returned 422 for malformed URL"
echo

echo "== All smoke tests passed =="