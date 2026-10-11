# Purpose: Build the orchestrator HTTP service with isolated dependencies.
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/orchestrator/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY contracts /app/contracts
COPY tests/fixtures /fixtures
COPY services/orchestrator /app
EXPOSE 8000
CMD ["uvicorn", "src.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
