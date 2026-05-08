FROM python:3.14

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-dev \
    libglx-mesa0 \
    libgl1 \
    make \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 smplfrm && \
    useradd -u 1000 -g 1000 -m -s /bin/bash smplfrm

WORKDIR /app

COPY . /app

RUN make packages

COPY docker/images/entrypoint.sh /app/entrypoint.sh

# Create writable directories and set ownership
# - db: SQLite database and migrations
# - staticfiles: collectstatic output
# - local_venv: Python virtual environment (needs write for .pyc caches)
# - /app: VERSION file written at startup, .cache for spotipy tokens
RUN mkdir -p /app/src/smplfrm/db /app/src/smplfrm/staticfiles && \
    chown -R smplfrm:smplfrm /app && \
    apt-get update && apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8321

ENTRYPOINT ["/app/entrypoint.sh"]
