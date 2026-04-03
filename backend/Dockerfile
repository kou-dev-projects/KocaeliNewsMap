# syntax=docker/dockerfile:1.7

FROM python:3.13-slim-bookworm AS builder

ARG INSTALL_ML=false
ARG INSTALL_DEV_TOOLS=false
ARG INSTALL_OPTIONAL_INTEGRATIONS=false

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt requirements-dev.txt ./
COPY requirements ./requirements

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --prefix=/install -r requirements.txt \
    && if [ "$INSTALL_ML" = "true" ]; then python -m pip install --prefix=/install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple torch; fi \
    && if [ "$INSTALL_ML" = "true" ]; then python -m pip install --prefix=/install -r requirements/optional-ml.txt; fi \
    && if [ "$INSTALL_DEV_TOOLS" = "true" ]; then python -m pip install --prefix=/install -r requirements/dev-tools.txt; fi \
    && if [ "$INSTALL_OPTIONAL_INTEGRATIONS" = "true" ]; then python -m pip install --prefix=/install -r requirements/optional-integrations.txt; fi

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/hub

RUN groupadd -r appuser \
    && useradd -m -r -g appuser -d /home/appuser appuser \
    && mkdir -p /home/appuser/.cache/huggingface/hub \
    && chown -R appuser:appuser /home/appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app ./app

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
