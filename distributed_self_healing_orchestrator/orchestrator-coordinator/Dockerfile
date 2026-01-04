FROM python:3.12-slim
WORKDIR /app
COPY orchestrator-coordinator /app

RUN pip install --no-cache-dir requests pika fastapi uvicorn joblib pandas scikit-learn scipy

EXPOSE 5001

CMD ["python", "consumer.py"]
