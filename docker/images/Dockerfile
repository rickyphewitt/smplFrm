FROM python:3.14

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-dev \
    libglx-mesa0 \
    libgl1 \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN make packages

COPY docker/images/entrypoint.sh /app/entrypoint.sh

EXPOSE 8321

ENTRYPOINT ["/app/entrypoint.sh"]
