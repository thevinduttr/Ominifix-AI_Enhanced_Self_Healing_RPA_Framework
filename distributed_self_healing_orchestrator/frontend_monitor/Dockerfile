# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY frontend_monitor/package.json frontend_monitor/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend_monitor/src ./src
COPY frontend_monitor/index.html ./
COPY frontend_monitor/vite.config.js ./
COPY frontend_monitor/eslint.config.js ./

# Build for production
RUN npm run build

# Production stage - serve with nginx
FROM nginx:alpine

# Copy nginx config
COPY frontend_monitor/nginx.conf /etc/nginx/nginx.conf

# Copy built app from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
