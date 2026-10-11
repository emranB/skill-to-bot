# Purpose: Build the perception HTTP service with isolated dependencies.
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/perception/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY contracts /app/contracts
COPY tests/fixtures /fixtures
COPY services/perception /app
EXPOSE 8001
CMD ["uvicorn", "src.skill_extraction.skill_extraction:app", "--host", "0.0.0.0", "--port", "8001"]
