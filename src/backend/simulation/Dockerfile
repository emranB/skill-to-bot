# Purpose: Build the pinned CPU-rendered Panda drawing runtime.
FROM python:3.11-slim-bookworm AS wheels
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY src/backend/simulation/requirements.lock /requirements.lock
RUN pip wheel --no-cache-dir -r /requirements.lock -w /wheels
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends libosmesa6 libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY src/backend/simulation/requirements.lock /app/requirements.lock
COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.lock && pip check && rm -rf /wheels
COPY contracts /app/contracts
COPY tests/fixtures /fixtures
COPY src/backend/simulation /app
COPY evidence/manifest.json /evidence/manifest.json
COPY evidence/demonstrations /evidence/demonstrations
COPY src/scripts/evaluate.py /app/evaluate.py
EXPOSE 8002
CMD ["uvicorn", "src.drawing_environment.drawing_environment:app", "--host", "0.0.0.0", "--port", "8002", "--no-access-log"]
