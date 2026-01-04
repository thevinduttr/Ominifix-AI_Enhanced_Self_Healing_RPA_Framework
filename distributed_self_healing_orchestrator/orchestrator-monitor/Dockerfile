FROM python:3.12-slim
WORKDIR /app

# Copy monitor app (and related files) into the image
COPY orchestrator-monitor /app
# Copy trained/demo models into container at /models (model_server expects /app/../models)
COPY models /models

RUN pip install --no-cache-dir fastapi uvicorn[standard] requests pika joblib pandas scikit-learn scipy

EXPOSE 8000 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
