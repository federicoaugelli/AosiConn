FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY requirements_conflicts.txt .
RUN pip install --no-cache-dir --no-dependencies -r requirements_conflicts.txt

COPY app/. .

EXPOSE 8000

CMD ["python3", "main.py"]
