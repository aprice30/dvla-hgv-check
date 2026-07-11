# DVLA HGV Check - Development Guide

This repository contains the DVLA HGV Check system. It consists of:
1. **`backend`**: A FastAPI application that stores events in Firestore and runs asynchronous DVLA plate checks.
2. **`detection_engine`**: A YOLOv8 and PaddleOCR computer vision pipeline that detects license plates from motion events.

---

## 🚀 How to Run

Follow these steps to start the system.

### 1. Start the Backend API

First, install dependencies and run the FastAPI server. From the root directory:

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Run the API server
cd backend
python main.py
```
*The API health check will be live at: http://localhost:8000/health*

---

### 2. Start the Detection Engine

Ensure the backend API is running first, then start the camera detection engine. From the root directory:

```bash
# Enable API posting and run against the test video file
SEND_TO_API=true CAMERA_SOURCE=IMG_7396.mov python detection_engine/main.py
```

#### Settings & Environment Variables:
* `SEND_TO_API`: Set to `true` to post detections to the backend.
* `CAMERA_SOURCE`: Path to a video file (e.g. `IMG_7396.mov`) or a camera device index (e.g. `0` for your webcam).
* `API_URL`: (Optional) Defaults to `http://localhost:8000/api/event`.

---

## 🐳 Running with Docker Compose

You can spin up both the FastAPI backend and the detection engine services together using Docker Compose.

### 1. Configure Environment Variables
Create a `.env` file in the root directory:

```bash
DVLA_API_KEY=your_dvla_api_key_here
CAMERA_SOURCE=IMG_7396.mov
```

### 2. Start Services

To build the backend image and start the containers, run:

```bash
docker-compose up --build
```

* The backend API will be available at `http://localhost:8000`.
* The detection engine container will automatically start, wait for the backend container to spin up, and send event posts to `http://dvla-backend:8000/api/event`.
