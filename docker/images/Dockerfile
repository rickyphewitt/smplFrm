FROM python:3.14

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-dev \
    libglx-mesa0 \
    libgl1 \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image, pinned by version and digest.
# Keep the version in sync with .github/workflows/ci.yml and lint.yml
# (setup-uv `version`); it must be >= pyproject.toml ([tool.uv] required-version).
COPY --from=ghcr.io/astral-sh/uv:0.12.20@sha256:100047e74f30778ab704942321a09750d6158739573ff58bf3924085cc6cd2d8 /uv /uvx /bin/

# Create non-root user
RUN groupadd -g 1000 smplfrm && \
    useradd -u 1000 -g 1000 -m -s /bin/bash smplfrm

WORKDIR /app

# uv build settings (https://docs.astral.sh/uv/reference/environment/):
# - use the base image's Python 3.14; never download a managed interpreter
# - precompile bytecode so the environment works without runtime writes
# - copy (not hardlink) packages out of the build cache mount
ENV UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install runtime dependencies from uv.lock before copying the full source so
# this layer is reused when only application code changes. The dev dependency
# group (pytest, pre-commit, ...) is excluded from the image.
COPY Makefile pyproject.toml uv.lock .python-version /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    make packages UV_SYNC_FLAGS="--locked --no-dev"

COPY . /app

COPY docker/images/entrypoint.sh /app/entrypoint.sh

# Runtime: `uv run` uses the environment built above as-is and never resolves,
# downloads, or modifies it.
ENV UV_RUN_FLAGS=--no-sync

# Create writable directories and set ownership
# - db: SQLite database and migrations
# - staticfiles: collectstatic output
# - /app: VERSION file written at startup, .cache for spotipy tokens
RUN mkdir -p /app/src/smplfrm/db /app/src/smplfrm/staticfiles && \
    chown -R smplfrm:smplfrm /app && \
    apt-get update && apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8321

ENTRYPOINT ["/app/entrypoint.sh"]
