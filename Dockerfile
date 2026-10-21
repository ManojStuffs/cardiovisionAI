# ==========================================
# Stage 1: Build React Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend
# ==========================================
FROM python:3.11-slim

# System dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Create user with UID 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Pre-install CPU-only PyTorch (reduces build time and image size)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
COPY requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy source code and demo data
COPY afib/ ./afib/
COPY backend/ ./backend/
COPY demo_images/ ./demo_images/
COPY hf_ecg_model.py ./
COPY hf_predict.py ./

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create scratch directory for runtime file uploads and ensure permissions
RUN mkdir -p /app/scratch && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Standard port for Hugging Face Spaces is 7860 (Render/Railway inject custom $PORT)
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
EXPOSE 7860

# Run with Gunicorn WSGI server dynamically binding to $PORT (defaults to 7860)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 180 backend.server:app"]
