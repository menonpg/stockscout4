FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run server
CMD ["python", "-m", "uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8080"]
