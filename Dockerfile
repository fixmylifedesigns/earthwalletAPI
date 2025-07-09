FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
EXPOSE 8080

CMD bash -c 'gunicorn healthcheck:app --bind 0.0.0.0:8000 --workers 1 & gunicorn app:app --bind 0.0.0.0:8080 --workers 1'