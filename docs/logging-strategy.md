# Backend logging and exception strategy

## The three tools

| Tool | What it does | Visible where |
|------|-------------|---------------|
| `console.log/warn/error` | Writes to stdout/stderr | Server logs only (Render, terminal) |
| `Sentry.captureException` | Sends event to Sentry | Sentry dashboard |
| Bubble up (throw/rethrow) | Error reaches `setupExpressErrorHandler` | Sentry dashboard (via `beforeSend`) |

---

## The rule: one path to Sentry

**Do not call `Sentry.captureException` manually.**

Let errors bubble up. `setupExpressErrorHandler` + `beforeSend` handle all Sentry capture automatically:

```
throw error (or rethrow)
    ↓
asyncHandler → next(error)
    ↓
setupExpressErrorHandler → Sentry.captureException (with trace)
    ↓
beforeSend → filter dev events, filter 400/404s
    ↓
errorHandler → HTTP response
```

Manual `captureException` causes **double capture** — Sentry receives the same error twice, inflating event counts and costs.

---

## When to use each tool

### `console.log`
**Only for startup and lifecycle events.**

```ts
// ✅ Good
console.log(`Server started on port ${PORT}`);
console.log(`API docs: http://localhost:${PORT}/api-docs`);

// ❌ Bad — use structured exception instead
console.log('Court created:', court.id);
```

### `console.warn`
**Only for transient, retryable conditions during the retry loop.**
Stop warning once retries are exhausted — let the error bubble.

```ts
// ✅ Good — warn on each retry attempt (local logs only)
console.warn(`Court update retry ${attempt + 1}/${MAX_RETRIES}: deadlock`);

// ❌ Bad — don't warn AND captureException for the same event
console.warn('Court update failed:', error);
Sentry.captureException(error); // ← remove this
```

### `console.error`
**Do not use.** If something is an error, throw an exception and let it bubble.
`console.error` goes to Sentry via `consoleLoggingIntegration`, creating noise without stack traces or proper context.

```ts
// ❌ Bad
console.error('Court update failed:', { courtId: id });
Sentry.captureException(error); // double capture

// ✅ Good — just throw/rethrow
throw new DatabaseException('Court update failed', error);
```

### `Sentry.captureException` (direct)
**Do not use in application code.** The only acceptable use is in `instrument.ts` (`beforeSend`) or a top-level unhandled rejection handler.

```ts
// ❌ Bad — manual capture in model/route
Sentry.withScope((scope) => {
  scope.setTag('operation', 'court_update');
  Sentry.captureException(error);
});

// ✅ Good — throw and let the pipeline handle it
throw error; // setupExpressErrorHandler captures with full trace context
```

---

## Adding context to Sentry events without manual capture

If you need DB-specific tags/context on a Sentry event, use `Sentry.getCurrentScope()` before rethrowing — the context is attached to the active transaction and picked up by `setupExpressErrorHandler`:

```ts
// ✅ Add context, then rethrow — no manual captureException needed
Sentry.getCurrentScope().setTag('error_type', isDeadlock ? 'deadlock' : 'lock_timeout');
Sentry.getCurrentScope().setContext('database_error', {
  error_code: error.code,
  court_id: id,
  retry_attempts: attempt + 1,
});
throw error; // setupExpressErrorHandler picks this up with the context attached
```

---

## Decision table

| Scenario | Action |
|----------|--------|
| Server startup | `console.log` |
| Retrying a transient error (not yet exhausted) | `console.warn` (local only) |
| Retries exhausted / fatal error | `throw` or `rethrow` — bubble up |
| Need rich context in Sentry | `Sentry.getCurrentScope().setTag/setContext`, then `throw` |
| User input error (400) | `throw new ValidationException(...)` — `beforeSend` drops it |
| Not found (404) | `throw new NotFoundException(...)` — `beforeSend` drops it |
| Database error | `throw new DatabaseException(...)` — bubbles to Sentry |
| Rate limit | `throw new RateLimitException(...)` — bubbles to Sentry |
| Development environment | Everything — `beforeSend` drops all dev events |

---

## What to remove from the codebase (tracked in CourtPulse-kyc)

| File | Line(s) | Action |
|------|---------|--------|
| `src/models/Court.ts` | 309 | Remove `console.error` — rethrow handles it |
| `src/models/Court.ts` | 313–345 | Replace `Sentry.withScope + captureException` with `Sentry.getCurrentScope()` + `throw` |
| `src/models/Court.ts` | 348–357 | Same — replace with scope tags + `throw` |
| `src/routes/courts.ts` | 173 | Remove `console.log('Court created:')` |
| `src/middleware/rateLimiter.ts` | 15 | Remove `console.warn` — `RateLimitException` bubbles to Sentry |
