# Sentry Setup for CourtPulse

## Overview
Sentry has been integrated into the CourtPulse backend to provide real-time error monitoring and performance tracking.

## Environment Variables

Add the following environment variable to your `.env` file:

```bash
# Sentry Configuration
SENTRY_DSN=your_sentry_dsn_here
```

## How to Get Your Sentry DSN

1. Go to [sentry.io](https://sentry.io) and create an account
2. Create a new project for "Node.js"
3. Copy the DSN from your project settings
4. Add it to your `.env` file

## What's Monitored

### Backend (Node.js/Express)
- **API Errors**: All Express route errors are captured
- **Database Errors**: PostgreSQL connection and query errors
- **Rate Limiting**: API rate limit exceeded errors
- **Validation Errors**: Request validation failures
- **Critical Errors**: Database, connection, and rate limit errors

### Environments
- **Development**: All errors sent to Sentry (100% sampling)
- **Staging**: All errors sent to Sentry (10% performance sampling)
- **Production**: All errors sent to Sentry (10% performance sampling)

## Error Context

Each error sent to Sentry includes:
- Request method, URL, and headers
- User agent and IP address
- Error type and stack trace
- Custom context from your logging system

## Integration Details

### Files Modified
- `backend/package.json` - Added @sentry/node dependency
- `backend/index.ts` - Sentry initialization and configuration
- `backend/src/middleware/errorHandler.ts` - Enhanced to send errors to Sentry
- `backend/logger.ts` - Enhanced to send critical errors to Sentry

### Existing Logging Preserved
Your existing structured logging system remains unchanged. Sentry complements it by providing:
- Real-time error alerts
- Error grouping and deduplication
- Performance monitoring
- User impact analysis

## Testing

To test Sentry integration:

1. Set your `SENTRY_DSN` in `.env`
2. Start the backend: `npm run dev`
3. Make a request to a non-existent endpoint: `GET /api/nonexistent`
4. Check your Sentry dashboard for the 404 error

### Quick Test Commands

```bash
# Test 404 error
curl http://localhost:5000/api/nonexistent

# Test health endpoint (should work)
curl http://localhost:5000/health

# Test courts endpoint (should work)
curl http://localhost:5000/api/courts
```

## Next Steps

This completes the **crawl** phase. Future phases will add:
- **Walk**: Frontend Sentry integration
- **Run**: Data pipeline Sentry integration
