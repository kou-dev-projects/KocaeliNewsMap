# ---- builder stage ----
FROM python:3.13-slim-bookworm AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage ----
FROM python:3.13-slim-bookworm

RUN groupadd -r appuser \
    && useradd -m -r -g appuser -d /home/appuser appuser \
    && mkdir -p /home/appuser/.cache/huggingface/hub \
    && chown -R appuser:appuser /home/appuser

ENV HOME=/home/appuser \
    HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/hub

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
