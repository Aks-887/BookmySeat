# Multi-stage production Dockerfile for BookMySeat

# Builder stage: install dependencies
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pip dependencies in a wheelhouse to cache layers
COPY requirements.txt ./
COPY requirements/email-providers.txt ./requirements-email-providers.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt || true
RUN if [ -f requirements/email-providers.txt ]; then pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-email-providers.txt || true; fi

# Final stage: runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# Copy wheels and install
COPY --from=builder /wheels /wheels
COPY --from=builder /usr/local/bin/pip /usr/local/bin/pip
RUN pip install --no-cache /wheels/* || true

# Copy project
COPY . /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app

USER appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Expose the standard gunicorn port
EXPOSE 8000

# Healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/_health/ || exit 1

# Entrypoint that runs migrations and collectstatic before launching
COPY deploy/entrypoint.sh /home/appuser/app/deploy/entrypoint.sh
RUN chmod +x /home/appuser/app/deploy/entrypoint.sh
ENTRYPOINT ["/home/appuser/app/deploy/entrypoint.sh"]

CMD ["gunicorn", "bookmyseat.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
