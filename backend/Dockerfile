FROM node:18-alpine

WORKDIR /app

# Copy package files from backend
COPY backend/package*.json ./

# Install all dependencies (including dev dependencies for build)
RUN npm ci

# Copy entire project (needed for shared directory)
COPY . .

# Build the TypeScript code (before removing dev dependencies)
RUN cd backend && npm run build

# Remove dev dependencies to reduce image size
RUN npm prune --production

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Change ownership
RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 5000

# Start from backend directory
WORKDIR /app/backend
CMD ["npm", "start"]