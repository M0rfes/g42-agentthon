FROM memgraph/memgraph-mage:latest

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    MEMGRAPH_URI=bolt://127.0.0.1:7687

USER root

# Install Python tooling and build dependencies for the API container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    curl \
    git \
    bash \
    procps \
    && python3 -m venv "$VIRTUAL_ENV" \
    && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Install Playwright Chromium browser and its system dependencies.
RUN playwright install --with-deps chromium

COPY . .

RUN mkdir -p /app/logs /var/lib/memgraph /var/log/memgraph \
    && chmod +x /app/entrypoint.sh \
    && chown -R memgraph:memgraph /app /var/lib/memgraph /var/log/memgraph /opt/venv

USER memgraph

EXPOSE 8000 7687

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "run:app"]
