# Use a small Python 3 base image (slim variant)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY app.py .

# Default command to run the app
CMD ["python", "app.py"]