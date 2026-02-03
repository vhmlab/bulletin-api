FROM python:3.14.2-slim AS builder

ENV PYTHONUNBUFFERED=1
WORKDIR /wheels

# Install build dependencies required to build wheels
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
		build-essential \
		gcc \
		libffi-dev \
		libssl-dev \
		python3-dev \
		cargo \
		rustc && \
	rm -rf /var/lib/apt/lists/*

# Build wheels for all requirements so final image doesn't need build deps
COPY requirements.txt /wheels/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
	pip wheel --no-cache-dir --wheel-dir /wheels -r /wheels/requirements.txt


FROM python:3.14.2-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install minimal runtime libs needed at runtime
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
		ca-certificates \
		curl && \
	rm -rf /var/lib/apt/lists/*

# Copy prebuilt wheels and install from them (no build tools needed)
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
	pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt

# Create non-root user before copying files so we can use --chown
RUN useradd --create-home --shell /bin/sh appuser

# Copy only the application package and required files and set ownership in one step
COPY --chown=appuser:appuser app/ /app/app
COPY --chown=appuser:appuser requirements.txt /app/requirements.txt

USER appuser

# Default DB path left to runtime with DATABASE_URL env
EXPOSE 18010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18010", "--workers", "4"]
