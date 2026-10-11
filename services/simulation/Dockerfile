# Purpose: Build the CPU-rendered LIBERO, robosuite, and MuJoCo simulation runtime.
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa LIBERO_CONFIG_PATH=/opt/libero-config
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends git build-essential libosmesa6 libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY services/simulation/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
RUN git clone https://github.com/Lifelong-Robot-Learning/LIBERO.git /opt/libero && cd /opt/libero && git checkout 8f1084e3132a39270c3a13ebe37270a43ece2a01 && pip install --no-cache-dir --no-deps -e . && mkdir -p /opt/libero-config /opt/libero/libero/datasets
COPY services/simulation/libero-config.yaml /opt/libero-config/config.yaml
COPY contracts /app/contracts
COPY tests/fixtures /fixtures
COPY services/simulation /app
EXPOSE 8002
CMD ["uvicorn", "src.simulation_environment.simulation_environment:app", "--host", "0.0.0.0", "--port", "8002"]
