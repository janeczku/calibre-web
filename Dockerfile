# --- Stage 1: Build the React Frontend SPA ---
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend

# Copy frontend source files
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Create the python runtime container ---
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install system dependencies for Qalibre
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libmagic1 \
    unrar-free \
    imagemagick \
    libxml2-dev \
    libxslt-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies list
COPY requirements.txt optional-requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r optional-requirements.txt || true

# Copy python backend code
COPY cps.py ./
COPY cps/ ./cps/
COPY library/ ./library/

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Expose Qalibre default port
EXPOSE 8083

# Run Qalibre server
CMD ["python", "cps.py"]
