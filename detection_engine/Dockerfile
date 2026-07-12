# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to keep dependencies clean and easy to copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and pre-install CPU-only PyTorch to prevent installing heavy CUDA binaries
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3.11-slim AS runner

WORKDIR /app

# Copy the virtual environment containing all dependencies from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install only runtime system dependencies (OpenCV & PaddlePaddle requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the application files preserving the package folder structure
COPY . ./detection_engine

# Set environment variables
ENV KMP_DUPLICATE_LIB_OK=TRUE
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV ULTRALYTICS_TELEMETRY=false
ENV YOLO_VERBOSE=false
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "detection_engine.main"]

