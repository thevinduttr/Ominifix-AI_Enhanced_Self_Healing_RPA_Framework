FROM mcr.microsoft.com/playwright/python:v1.53.0-noble
WORKDIR /app
COPY dummy_bot /app
RUN pip install --no-cache-dir requests selenium playwright==1.53.0
CMD ["python", "bot.py"]
