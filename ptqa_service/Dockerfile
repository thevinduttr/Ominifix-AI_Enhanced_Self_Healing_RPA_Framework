# Use official Playwright image which has all browser dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.53.0-noble

WORKDIR /app

# Network-hardened pip defaults for large wheel downloads in unstable environments.
ENV PIP_DEFAULT_TIMEOUT=180 \
	PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install \
	--retries 20 \
	--timeout 180 \
	--resume-retries 10 \
	-r requirements.txt

# Playwright browsers already bundled in base image — just ensure chromium is ready
RUN python -m playwright install chromium

COPY app ./app
COPY bots ./bots
COPY static ./static
COPY templates ./templates
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
