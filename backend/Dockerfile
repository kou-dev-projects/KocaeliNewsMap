# syntax=docker/dockerfile:1.7

FROM python:3.13-slim-bookworm AS builder

ARG INSTALL_ML=false
ARG INSTALL_DEV_TOOLS=false
ARG INSTALL_OPTIONAL_INTEGRATIONS=false

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_CACHE_DIR=/root/.cache/pip \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt ./requirements.txt
COPY requirements/runtime.txt ./requirements/runtime.txt

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m pip install --prefix=/install -r requirements.txt

COPY requirements/torch-cpu.txt requirements/optional-ml.txt ./requirements/

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "$INSTALL_ML" = "true" ]; then \
        python -m pip install --prefix=/install -r requirements/torch-cpu.txt; \
        python -m pip install --prefix=/install -r requirements/optional-ml.txt; \
    fi

COPY requirements/dev-tools.txt ./requirements/dev-tools.txt

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "$INSTALL_DEV_TOOLS" = "true" ]; then \
        python -m pip install --prefix=/install -r requirements/dev-tools.txt; \
    fi

COPY requirements/optional-integrations.txt ./requirements/optional-integrations.txt

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "$INSTALL_OPTIONAL_INTEGRATIONS" = "true" ]; then \
        python -m pip install --prefix=/install -r requirements/optional-integrations.txt; \
    fi

FROM python:3.13-slim-bookworm AS runtime

ARG INSTALL_PLAYWRIGHT_BROWSER=true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/hub \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN groupadd -r appuser \
    && useradd -m -r -g appuser -d /home/appuser appuser \
    && mkdir -p /home/appuser/.cache/huggingface/hub \
    && chown -R appuser:appuser /home/appuser

WORKDIR /app

COPY --from=builder /install /usr/local

RUN if [ "$INSTALL_PLAYWRIGHT_BROWSER" = "true" ]; then python -m playwright install --with-deps chromium; fi \
    && if [ -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then chmod -R a+rX "$PLAYWRIGHT_BROWSERS_PATH"; fi

COPY app ./app

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
