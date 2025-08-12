FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    python3 \
    python3-pip \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtual env
RUN python3 -m venv venv

# Activate venv and upgrade pip/install requirements
RUN . ./venv/bin/activate && pip install --upgrade pip
COPY requirements.txt .
RUN . ./venv/bin/activate && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/bin/bash", "-c", ". ./venv/bin/activate && python app.py"]