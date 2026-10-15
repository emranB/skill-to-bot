# Purpose: Build the drawing persistence and workflow HTTP service.
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY src/backend/orchestrator/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && pip check
COPY contracts /app/contracts
COPY tests/fixtures /fixtures
COPY src/backend/orchestrator /app
EXPOSE 8000
CMD ["uvicorn", "src.api.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
