ARG PYTHON_VERSION="3.11"
FROM mcr.microsoft.com/devcontainers/python:${PYTHON_VERSION}

# System dependencies that are often needed (psycopg2, Pillow, build tools)
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       libjpeg-dev \
       zlib1g-dev \
       libffi-dev \
       curl \
       git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces
