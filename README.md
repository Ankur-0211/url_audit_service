# URL Audit Service

A production-grade REST API that audits a target URL — reachability, response time, status code, basic SEO/meta signals, and security headers — built as a timed (4-hour) design-to-deploy exercise.

---
**Built for Digital Heroes Training Task** — [digitaheroesco.com](https://digitaheroesco.com)
---

**Live service:** https://url-audit-service-759m.onrender.com/
**Docs (Swagger UI):** https://url-audit-service-759m.onrender.com//docs
**Full architecture & design rationale:** [`docs/SOFTWARE_DESIGN_DOCUMENT.md`](docs/SOFTWARE_DESIGN_DOCUMENT.md)

> **Scope note:** This submission covers **Task A** (a working, deployed, production-grade single-instance service) as a full implementation, and **Task B** (scaling to 10,000 audits/day / 500 concurrent requests) as a **written design only** — see [§20 of the SDD](docs/SOFTWARE_DESIGN_DOCUMENT.md#20-scaling-design-task-b). Task B is explicitly not implemented in code; that boundary is intentional and stated per the original constraint.

---

## What it does

`POST /audit` with a URL, and the service:
1. Validates the URL (format, scheme, length) and blocks anything resolving to a private/loopback/reserved IP (SSRF guard, re-checked on every redirect hop).
2. Fetches it with a hard 5-second timeout, bounded outbound concurrency, and no retries.
3. Parses the response for status code, timing, title, meta description, `h1` count, and presence of key security headers.
4. Caches the result in-memory (TTL 300s) so repeat requests for the same URL are near-instant.
5. Rate-limits callers per IP (10 requests/60s by default) to protect the single instance.

Every response and error carries a `request_id`, echoed in an `X-Request-ID` header and in structured JSON logs, so any reported issue can be traced directly to a server-side log line.

---

## Quick start (local)

```bash
git clone <your-repo-url>
cd url-audit-service
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/docs` for interactive Swagger UI, or:

```bash
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Running tests

```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

All outbound HTTP is mocked (`respx`) — no real network access needed to run the suite. Current coverage: **95%** overall, all core layers (`services/`, `core/`, `cache/`, `middleware/`) above the 80% target.

---

## API summary

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/audit` | Run an audit on a supplied URL |
| `GET` | `/health` | Liveness probe (no downstream deps) |
| `GET` | `/` | Service metadata |
| `GET` | `/docs` | Interactive Swagger UI |

**Example request:**
```json
POST /audit
{"url": "https://example.com"}
```

**Example success response:**
```json
{
  "url": "https://example.com",
  "final_url": "https://example.com/",
  "status_code": 200,
  "reachable": true,
  "response_time_ms": 184,
  "redirected": false,
  "redirect_chain": [],
  "content_type": "text/html; charset=UTF-8",
  "title": "Example Domain",
  "meta_description": null,
  "h1_count": 1,
  "security_headers": {
    "strict_transport_security": false,
    "content_security_policy": false,
    "x_content_type_options": false,
    "x_frame_options": false
  },
  "cached": false,
  "audited_at": "2026-07-25T09:12:41Z",
  "request_id": "b6f1c8f0-2b0a-4d0a-9d3a-6f8f9d0a1b2c"
}
```

Errors share one envelope:
```json
{
  "error": {
    "code": "URL_NOT_ALLOWED",
    "message": "The requested host resolves to a disallowed address range",
    "request_id": "...",
    "details": {}
  }
}
```

| Status | `code` | Trigger |
|---|---|---|
| 400/422 | `VALIDATION_ERROR` | Missing/malformed `url`, bad scheme, over max length |
| 403 | `URL_NOT_ALLOWED` | SSRF guard blocked the resolved IP |
| 408 | `TARGET_TIMEOUT` | Target didn't respond within 5s |
| 502 | `TARGET_UNREACHABLE` | DNS failure / connection refused / TLS error |
| 413 | `PAYLOAD_TOO_LARGE` | Request body over 10KB |
| 429 | `RATE_LIMIT_EXCEEDED` | Caller over their per-IP rate limit |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

Full contract in [SDD §2 and §8](docs/SOFTWARE_DESIGN_DOCUMENT.md#2-functional-requirements).

---

## Architecture (summary)

Client → Middleware (request ID, payload size, rate limit)
→ Route handler → Schema + SSRF validation
→ Cache lookup (hit → return; miss → continue)
→ Audit Service → HTTP Client (timeout, semaphore, redirect-safe)
→ Analyzer (headers + HTML parsing, pure function)
→ Cache write → Structured response

Layered so business logic (`services/`) never touches the HTTP framework directly, and `cache/`/`middleware/rate_limiter.py` are built with interfaces designed to be swapped for Redis-backed equivalents in Task B with zero changes to `services/audit_service.py`. Full diagrams and rationale: [SDD §4](docs/SOFTWARE_DESIGN_DOCUMENT.md#4-high-level-architecture).

## Security

- Pydantic `AnyHttpUrl` + explicit length cap reject malformed/oversized input at the edge.
- SSRF guard resolves and checks every hostname against private/loopback/link-local/reserved ranges — re-validated on **every redirect hop**, capped at 3 hops.
- Request body size capped at 10KB via a `Content-Length` check before any parsing.
- No secrets required or logged; full request/response bodies of audited pages are never logged.

Full detail: [SDD §13](docs/SOFTWARE_DESIGN_DOCUMENT.md#13-security-considerations).

## Observability

- Structured JSON logs to stdout, one line per request lifecycle event and per audit outcome, all correlated by `request_id` via a contextvar.
- `X-Request-ID` header on every response (success or error) matches the log lines for that request.
- `/health` has zero downstream dependencies, so it never false-positives during a slow outbound audit elsewhere in the process.

Full detail: [SDD §16 and §23](docs/SOFTWARE_DESIGN_DOCUMENT.md#16-logging-strategy).

## Task B — Scaling to 10,000 audits/day, 500 concurrent (design only)

Not implemented. Full written design — capacity math, architecture diagram, SLA/SLO definitions, failure isolation, and the exact Task A → Task B migration path — is in [SDD §20](docs/SOFTWARE_DESIGN_DOCUMENT.md#20-scaling-design-task-b). Short version: in-memory cache and rate limiter move to Redis, synchronous request/response becomes an async job queue (`202 Accepted` + polling), execution moves to an autoscaled worker pool, and results persist to Postgres — all built on interfaces already present in the Task A code (§14, §15) specifically so this is an extension, not a rewrite.

## Known limitations (Task A)

- Render free tier cold-starts after inactivity — first request after idle time may be slow. Documented, not a defect ([ADR-005](docs/SOFTWARE_DESIGN_DOCUMENT.md#21-technology-decision-record-adr)).
- Cache and rate limiter are per-instance and reset on restart — acceptable for a single-instance demo, explicitly closed by the Task B design (§14, §15, §20).
- No JavaScript-rendered page auditing (headless browser) — out of scope for both tasks.

## Tech stack

Python 3.12 · FastAPI · httpx · BeautifulSoup4 + lxml · pydantic-settings · pytest + respx · GitHub Actions · Render

