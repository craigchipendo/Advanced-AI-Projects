FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Build deps + Postgres client libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    postgresql postgresql-client postgresql-contrib \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app

# Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# HuggingFace token (pass at runtime: docker run --env-file .env ...)
# HUGGINGFACEHUB_API_TOKEN is read from the environment at runtime.
# Do NOT bake it into the image.

EXPOSE 8000 5432
CMD ["/entrypoint.sh"]
