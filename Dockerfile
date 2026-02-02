# Builder stage: build wheels for all dependencies
########################################################
# Builder stage (Debian slim): build and install deps
########################################################
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1

# Install build dependencies needed for compiling wheels
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev cargo git ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt /app/

RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies into /install so we can copy only needed files to distroless
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy application source into install location
COPY . /install/app


########################################################
# Final stage (Distroless): minimal runtime image
########################################################
FROM gcr.io/distroless/python3:nonroot

WORKDIR /app

# Copy installed packages and app from builder
COPY --from=builder /install /usr/local
COPY --from=builder /install/app /app

EXPOSE 18010

# Ensure Python finds packages installed into /usr/local
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages:/usr/local/lib/python3.11/dist-packages

# Distroless image already provides `python` as the entrypoint; pass module args directly
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18010"]
