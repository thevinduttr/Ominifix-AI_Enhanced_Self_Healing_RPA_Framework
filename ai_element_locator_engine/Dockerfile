FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY data ./data

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8001"]
