# Use official Playwright image which has all browser dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers already bundled in base image — just ensure chromium is ready
RUN python -m playwright install chromium

COPY app ./app
COPY bots ./bots
COPY static ./static
COPY templates ./templates
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
