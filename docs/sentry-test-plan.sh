#!/usr/bin/env bash
# Sentry live test script — CourtPulse backend
#
# SETUP: Start the backend with staging environment so beforeSend lets events through:
#   cd backend && SENTRY_ENVIRONMENT=staging NODE_ENV=staging npx ts-node --esm index.ts
#
# Then run this script in a separate terminal:
#   bash docs/sentry-test-plan.sh
#
# After running, verify each pillar in the Sentry dashboard.

BASE="http://localhost:5001"

echo ""
echo "=========================================="
echo "  CourtPulse — Sentry Live Test Script"
echo "=========================================="
echo ""

# ── PILLAR 1A: Unhandled error (should appear in Sentry Issues)
echo "[1A] Triggering unhandled error → expect 1 event in Sentry Issues"
curl -s -o /dev/null -w "  Status: %{http_code}\n" "$BASE/api/courts/test-error"
echo "  ✓ Check Sentry Issues for: 'intentional unhandled error from /api/courts/test-error'"
echo ""

# ── PILLAR 1B: 400 and 404 (should NOT appear in Sentry Issues)
echo "[1B] Triggering 400 (zoom too low) → should NOT appear in Sentry Issues"
curl -s -o /dev/null -w "  Status: %{http_code}\n" "$BASE/api/courts/search?zoom=5"
echo ""

echo "[1B] Triggering 404 (unknown route) → should NOT appear in Sentry Issues"
curl -s -o /dev/null -w "  Status: %{http_code}\n" "$BASE/api/nonexistent-route"
echo ""

# ── PILLAR 2A: Zero results warn (should appear in Sentry Logs)
# bbox is in the middle of the Pacific Ocean — guaranteed zero courts
echo "[2A] Searching in Pacific Ocean (zero results) → expect warn in Sentry Logs"
curl -s -o /dev/null -w "  Status: %{http_code}\n" \
  "$BASE/api/courts/search?bbox=-160,-20,-150,-10&zoom=14"
echo "  ✓ Check Sentry Logs for: 'Court search returned zero results' with bbox/zoom attrs"
echo ""

# ── PILLAR 2B: Rate limit exceeded (should appear in Sentry Logs + Metrics)
echo "[2B] Sending 22 requests to exceed rate limit → expect warn in Sentry Logs"
for i in $(seq 1 22); do
  curl -s -o /dev/null "$BASE/api/courts/search?bbox=-160,-20,-150,-10&zoom=14"
done
echo "  Sent 22 requests."
echo "  ✓ Check Sentry Logs for: 'Rate limit exceeded' with endpoint + IP attrs"
echo "  ✓ Check Sentry Metrics for: rate_limit.exceeded counter"
echo ""

# ── PILLAR 3: Trace (should appear in Sentry Performance)
echo "[3]  Normal search → expect trace in Sentry Performance with DB spans"
curl -s -o /dev/null -w "  Status: %{http_code}\n" \
  "$BASE/api/courts/search?bbox=-122.45,-37.80,-122.35,-37.75&zoom=14"
echo "  ✓ Check Sentry Performance for Express route trace + DB child spans"
echo ""

# ── PILLAR 4: Metrics (should appear in Sentry Metrics/Explore)
echo "[4]  Running 5 searches to populate court_search metrics..."
for i in $(seq 1 5); do
  curl -s -o /dev/null "$BASE/api/courts/search?bbox=-122.45,-37.80,-122.35,-37.75&zoom=14"
done
echo "  Sent 5 searches."
echo "  ✓ Check Sentry Metrics/Explore for:"
echo "     - court_search.count (counter)"
echo "     - court_search.results (distribution — p50/p95)"
echo "     Note: metrics may take 1-2 minutes to appear in UI"
echo ""

echo "=========================================="
echo "  All test scenarios triggered."
echo "  Open Sentry and verify each pillar:"
echo "    Issues    → 1 unhandled error, no 400/404"
echo "    Logs      → zero-results warn, rate limit warn"
echo "    Perf      → traces with DB spans"
echo "    Metrics   → court_search.count, court_search.results, rate_limit.exceeded"
echo "=========================================="
echo ""
