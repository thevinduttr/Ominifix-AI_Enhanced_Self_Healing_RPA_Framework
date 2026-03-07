FROM python:3.12-slim
WORKDIR /app
COPY dummy_bot /app
RUN pip install --no-cache-dir requests selenium
CMD ["python", "bot.py"]
