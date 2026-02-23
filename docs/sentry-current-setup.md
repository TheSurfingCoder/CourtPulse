# Sentry – current backend setup

## Packages
- `@sentry/node` v10.17.0
- `@sentry/profiling-node` v10.17.0
- `@sentry/cli` v2.56.0 (source map upload on build)

---

## Initialization (`backend/instrument.ts`)
| Setting | Value |
|---------|-------|
| DSN | `process.env.SENTRY_DSN` |
| Environment | `SENTRY_ENVIRONMENT` → `NODE_ENV` → `'development'` |
| Release | `backend@{npm_package_version}` (fallback: `1.1.0`) |
| `sendDefaultPii` | `true` (request headers + IP captured) |
| `tracesSampleRate` | `0.1` in production, `1.0` in development |
| `profilesSampleRate` | `0.1` in production, `1.0` in development |
| `enableLogs` | `true` (console output forwarded to Sentry) |

**Integrations:**
- `nodeProfilingIntegration()` — CPU profiling
- `consoleLoggingIntegration({ levels: ["log", "warn", "error"] })` — all console output forwarded to Sentry

**Note:** `beforeSend` filter to drop dev events is currently commented out. Dev events are reaching Sentry.

---

## Exception hierarchy (`src/exceptions/index.ts`)

```
AppException (base — isOperational: true)
├── ValidationException (400)
│   ├── InvalidCoordinatesException
│   ├── InvalidBboxException
│   ├── InvalidIdException
│   ├── MissingFieldsException
│   └── ZoomLevelException
├── NotFoundException (404)
│   ├── CourtNotFoundException
│   └── RouteNotFoundException
├── ConflictException (409)
│   └── DuplicateCourtException
├── DatabaseException (500)
│   ├── DeadlockException
│   └── LockTimeoutException
├── TransientException (503)
└── RateLimitException (429)
```

Each exception carries: `message`, `statusCode`, `code` (machine-readable), and `isOperational`.

---

## Route layer (`src/routes/courts.ts`)

### How async/await, asyncHandler, and errorHandler work together

#### Block 1: Normal function vs async function

```ts
// Normal function — throws synchronously, caught immediately
function normal() {
  throw new Error("oops");
}

// Async function — always returns a Promise
async function asyncFn() {
  throw new Error("oops");
}
// Does NOT throw. Returns: Promise.reject(Error("oops"))
// The error is "inside" the Promise
```

#### Block 2: What Express expects from a route

Express routes receive `(req, res, next)`. When something goes wrong, you call `next(error)` — that tells Express to skip all remaining normal middleware and jump to the error handler:

```ts
app.get('/courts/:id', (req, res, next) => {
  const court = findCourt(id);
  if (!court) {
    next(new Error("court not found"));  // tell Express "something went wrong"
    return;
  }
  res.json({ data: court });
});
```

This works fine for synchronous code. But modern routes `await` database calls — and Express doesn't automatically know when an async function fails.

#### Block 3: Why async breaks Express error handling

Express was built before `async/await`. When it calls an async route, it doesn't wait for the Promise — it moves on immediately. So if the route throws, Express never sees it:

```ts
// ❌ Without asyncHandler — Express misses the error
app.get('/courts/:id', async (req, res, next) => {
  const court = await CourtModel.findById(id);
  if (!court) {
    throw new CourtNotFoundException(id);
    // becomes Promise.reject(...)
    // Express already moved on — never sees this
    // Request hangs forever, or process crashes with UnhandledPromiseRejection
  }
  res.json({ data: court });
});
```

#### Block 4: How asyncHandler fixes it

`asyncHandler` is a wrapper that bridges async functions and Express's `next(error)`:

```ts
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
  // If the Promise rejects (route threw), .catch(next) calls next(error)
  // Express then sees next(error) and jumps to errorHandler
};
```

```ts
// ✅ With asyncHandler — error is caught and passed to Express
router.get('/:id', asyncHandler(async (req, res) => {
  const court = await CourtModel.findById(id);
  if (!court) {
    throw new CourtNotFoundException(id);
    // → Promise.reject(CourtNotFoundException)
    // → .catch(next) → next(CourtNotFoundException)
    // → Express jumps to errorHandler
  }
  res.json({ data: court });
}));
```

#### Block 5: Full end-to-end flow

Example: `GET /api/courts/999` where court doesn't exist.

```
1. Request arrives → index.ts middleware chain (helmet, cors, json) — all pass through

2. Router matches /:id → asyncHandler wraps the async fn

3. Route runs:
   - id = 999 (valid number)
   - await CourtModel.findById(999) → null
   - throw new CourtNotFoundException(999)
   - async fn → Promise.reject(CourtNotFoundException)

4. asyncHandler: .catch(next) → next(CourtNotFoundException)

5. Express skips normal middleware, finds 4-arg handlers:
   - Sentry.setupExpressErrorHandler(app) → adds trace context
   - errorHandler → runs

6. errorHandler:
   - CourtNotFoundException extends NotFoundException → skip Sentry (not sent)
   - res.status(404).json({ success: false, error: '...', code: 'COURT_NOT_FOUND' })

7. Client receives:
   { "success": false, "error": "Court with ID 999 not found", "code": "COURT_NOT_FOUND" }
```

Same flow with a **database crash** (does go to Sentry):
```
DB throws → Court.ts wraps in DatabaseException → rethrows
→ asyncHandler .catch(next) → next(DatabaseException)
→ Sentry.setupExpressErrorHandler adds trace
→ errorHandler:
    scope.setLevel('error')       // DatabaseException = error severity
    Sentry.captureException(err)  // ✓ sent to Sentry
    res.status(500).json({ success: false, error: 'An unexpected error occurred', code: 'INTERNAL_ERROR' })
```

**Complete picture:**
```
Client request
    ↓
index.ts middleware (helmet → cors → json)
    ↓
courts.ts route → asyncHandler wraps async fn
    ↓
         ┌─── success → res.json() → Client
         │
         └─── throws → .catch(next) → next(error)
                              ↓
                  Sentry.setupExpressErrorHandler
                  (adds trace context)
                              ↓
                        errorHandler
                              ↓
                   ┌── ValidationException  → skip Sentry → 400
                   ├── NotFoundException    → skip Sentry → 404
                   ├── DatabaseException    → Sentry error → 500
                   └── Unknown error        → Sentry error → 500
```

---

- All routes wrapped in `asyncHandler` — async errors propagate to `errorHandler` automatically.
- Routes throw typed exceptions directly (no try-catch in routes). Examples:
  - `throw new ZoomLevelException(11)` — zoom too low
  - `throw new InvalidBboxException()` — bad bbox param
  - `throw new CourtNotFoundException(id)` — court not found
  - `throw new MissingFieldsException([...])` — missing POST body fields
- One `console.log('Court created:', court.id, court.name)` in the POST route — forwarded to Sentry via `consoleLoggingIntegration`.

---

## Error handler (`src/middleware/errorHandler.ts`)

This is the HTTP boundary — all errors flow here.

**What gets captured in Sentry:**
- `DatabaseException` and non-operational errors → `level: error`
- Other operational `AppException` types → `level: warning`

**What is skipped (not sent to Sentry):**
- `ValidationException` (user input errors, e.g. bad coordinates, missing fields)
- `NotFoundException` (user-facing 404s, e.g. court not found, unknown route)

**Context attached to every Sentry event:**
- Tags: `errorType`, `isOperational`, `errorCode`, `statusCode`
- Context: `method`, `url`, `path`, `query`, `userAgent`, `ip`

**Response format (consistent across all errors):**
```json
{ "success": false, "error": "...", "code": "..." }
```
Stack trace only exposed in `NODE_ENV=development`.

`Retry-After` header set for `RateLimitException` and `TransientException`.

---

## Model layer (`src/models/Court.ts`)

- `Sentry.captureException` called directly for deadlock and lock timeout errors before rethrowing as `DatabaseException`.
- Uses `Sentry.withScope()` with DB-specific tags for filtering.
- **Side effect:** these errors are captured twice — once here, once in `errorHandler`.

---

## Express setup (`backend/index.ts`)

- `Sentry.setupExpressErrorHandler(app)` registered before custom error middleware.
- CORS allows `sentry-trace` and `baggage` headers (distributed tracing support).

---

## Source maps

- Injected and uploaded to Sentry on `npm run build`.
- Org: `na-795`, Project: `node-express` (hardcoded in `package.json`).

---

## Environment variables required
| Variable | Purpose |
|----------|---------|
| `SENTRY_DSN` | Sentry project DSN |
| `SENTRY_ENVIRONMENT` | Environment label (e.g. `production`, `staging`) |
| `NODE_ENV` | Fallback for environment |
| `npm_package_version` | Set automatically by npm at runtime |

---

## Changes made (sentry-optimization branch)

### refactor: move filtering to beforeSend, remove captureException from errorHandler (commit 09ad76c)

**`instrument.ts`**
- Added `beforeSend` — drops all events in `development` environment; drops `ValidationException` and `NotFoundException` (400/404s) before they leave the server.
- Narrowed `consoleLoggingIntegration` from `["log", "warn", "error"]` to `["warn", "error"]` — removes `console.log` noise from Sentry.
- `tracesSampleRate` now environment-aware: `0.1` in production, `1.0` in development.

**`errorHandler.ts`**
- Removed all Sentry imports and logic (`Sentry.withScope`, `Sentry.captureException`, tags, context, severity).
- Now has single responsibility: transform errors into HTTP responses.
- `setupExpressErrorHandler` handles Sentry capture; `beforeSend` handles filtering.

---

## Remaining gaps
1. **Double capture in model layer** — `Sentry.captureException` called directly in `Court.ts` for deadlock/lock timeout errors; these will still be captured twice (once in model, once by `setupExpressErrorHandler`).
2. **No user context** — `sendDefaultPii: true` captures IP but `Sentry.setUser()` is never called; user identity not attached to events.
3. **Logging strategy undefined** — no clear rule for when to use `console.error` vs let errors bubble vs `Sentry.captureException` directly. See Beads epic `CourtPulse-wbp`.
4. **No dynamic sampling** — `tracesSampler` not configured; all routes sampled equally.
5. **Hardcoded org/project slug** — `na-795` / `node-express` in `package.json` build script.
