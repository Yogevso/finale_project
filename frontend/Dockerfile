# Build stage
FROM node:20-alpine3.20@sha256:3bc9a4c4cc25cfde1e8f946341c85f333c36517aafda829b4bb7e785e9b5995c AS builder

WORKDIR /app

ARG VITE_API_URL=/api/v1
ARG VITE_COLLAB_SERVER_URL=ws://localhost:8002

ENV VITE_API_URL="${VITE_API_URL}"
ENV VITE_COLLAB_SERVER_URL="${VITE_COLLAB_SERVER_URL}"

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build:docker

# Production stage - use unprivileged nginx behind a TLS-terminating proxy
FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the unprivileged port used by nginx-unprivileged
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1

# nginx-unprivileged runs as non-root by default
CMD ["nginx", "-g", "daemon off;"]
