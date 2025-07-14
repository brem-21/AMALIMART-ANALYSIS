# Use official Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8001

# Run FastAPI server
CMD ["uvicorn", "hybrid_recommender:app", "--host", "0.0.0.0", "--port", "8001"]
