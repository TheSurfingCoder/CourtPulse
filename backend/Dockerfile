FROM node:18-alpine

WORKDIR /app

# Copy entire project first
COPY . .

# Install backend dependencies
RUN cd backend && npm ci

# Build the TypeScript code (before removing dev dependencies)
RUN cd backend && npm run build

# Remove dev dependencies to reduce image size
RUN cd backend && npm prune --production

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Change ownership
RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 5000

# Start from backend directory where dist is located
WORKDIR /app/backend
CMD ["node", "dist/index.js"]