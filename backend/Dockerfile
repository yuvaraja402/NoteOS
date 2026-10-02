# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY requirements.txt .
RUN pip download --only-binary=:all: --require-hashes --dest /wheels -r requirements.txt

FROM base AS runtime
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels --require-hashes -r requirements.txt \
    && pip uninstall -y pip setuptools wheel \
    && rm -rf /wheels
COPY app ./app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
