# 📝 CourtPulse Logging Overview

CourtPulse uses **Pino** for structured logging across frontend and backend with environment-specific configurations.

## 🏗️ Architecture

```
Development:
Frontend → Browser Console + Backend API → Terminal (pretty formatted)
Backend → Terminal (pretty formatted)

Production:
Frontend → Nothing (no-op functions)
Backend → Terminal (JSON format, info level only)
```

## 📁 Key Files

- `shared/logger.ts` - Backend logger (Node.js)
- `frontend/lib/logger-with-backend.ts` - Frontend logger (browser + backend)
- `backend/src/routes/logs.ts` - API endpoint for frontend logs

## 🔧 Configuration

### Backend (`shared/logger.ts`)
- **Development**: `debug` level, pretty formatted with colors
- **Production**: `info` level, raw JSON for log aggregation

### Frontend (`logger-with-backend.ts`)
- **Development**: Logs to browser console + sends to backend API
- **Production**: No-op functions (zero overhead)

## 🚀 Usage

### Backend
```typescript
import { logEvent, logError, logBusinessEvent, logLifecycleEvent } from '../shared/logger.js';

logBusinessEvent('user_registered', { userId: user.id });
logError(error, { context: 'user_registration' });
logLifecycleEvent('server_started', { port: 5001 });
```

### Frontend
```typescript
import { logEvent, logError, logBusinessEvent } from '../lib/logger-with-backend';

logBusinessEvent('map_interaction', { action: 'zoom', zoomLevel: 12 });
logError(error, { component: 'CourtsMap' });
logEvent('component_render', { component: 'CourtsMap', renderCount: 1 });
```

## 🎯 Log Categories

- **Business Events**: User actions, API calls, feature usage
- **Lifecycle Events**: Server startup, database migrations
- **Error Events**: Exceptions, failures, validation errors
- **General Events**: Component renders, performance metrics

## 🔍 Log Levels

| Level | Numeric | Usage |
|-------|---------|-------|
| `error` | 50 | Exceptions, critical issues |
| `warn` | 40 | Deprecations, performance issues |
| `info` | 30 | Business events, lifecycle events |
| `debug` | 20 | Detailed debugging, verbose output |

## 🌍 Environment Behavior

### Development
- **Backend**: Pretty formatted logs with colors
- **Frontend**: Browser console + terminal (via `/api/logs`)
- **HTTP Requests**: Filtered out for `/api/logs` endpoint

### Production
- **Backend**: JSON format, info level only
- **Frontend**: Silent (no-op functions)

## 🔄 Frontend Log Forwarding

1. Frontend logs to browser console
2. Frontend sends log to `/api/logs` (async)
3. Backend receives and forwards to Pino
4. Terminal displays with `source: "frontend"`

## 📊 Log Structure

```json
{
  "level": 30,
  "time": "2025-09-22T13:39:53.791-07:00",
  "event": "event_name",
  "source": "frontend|backend",
  "data": { ... }
}
```

## 🚨 Best Practices

### Do's ✅
- Use structured logging with consistent event names
- Include relevant context in log data
- Log business events for analytics
- Use appropriate log levels

### Don'ts ❌
- Don't log sensitive information
- Don't use `console.log` directly
- Don't log excessive debug info in production

## 🔧 Troubleshooting

**Frontend logs not in terminal**: Check `NODE_ENV=development` and `/api/logs` endpoint
**Backend not pretty formatted**: Ensure `pino-pretty` installed and `NODE_ENV=development`
**Production too verbose**: Check `LOG_LEVEL=info` in production

## 📈 Performance

- **Development**: Minimal impact (async logging)
- **Production**: Zero frontend overhead, minimal backend impact
