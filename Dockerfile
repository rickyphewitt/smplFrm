FROM python:3.9

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY . /app

RUN ls -la

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
