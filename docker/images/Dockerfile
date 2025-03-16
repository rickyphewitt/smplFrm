FROM python:3.12

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-dev \
    libgl1-mesa-glx \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY ../.. /app

RUN make packages

CMD ["make", "run"]
