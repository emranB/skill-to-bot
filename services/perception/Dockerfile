# Purpose: Build the perception HTTP service with isolated dependencies.
FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1
ENV SEGMENTATION_MODEL=/app/models/yolov8n-seg.onnx
WORKDIR /app
COPY services/perception/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock \
 && mkdir -p /app/models \
 && python -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/mobilint/YOLOv8n-seg/resolve/main/yolov8n-seg.onnx', '/app/models/yolov8n-seg.onnx')" \
 && python -c "import hashlib, pathlib; digest=hashlib.sha256(pathlib.Path('/app/models/yolov8n-seg.onnx').read_bytes()).hexdigest(); assert digest=='cb1e689c548b3fa019691c9c1762f38a76276981ce75d31f6c5aae396dbff78b', digest"
COPY contracts /app/contracts
COPY tests/fixtures /fixtures
COPY services/perception /app
EXPOSE 8001
CMD ["uvicorn", "src.skill_extraction.skill_extraction:app", "--host", "0.0.0.0", "--port", "8001"]
