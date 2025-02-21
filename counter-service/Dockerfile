FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (including SQLite)
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000
CMD ["uvicorn", "counter_service:app", "--host", "0.0.0.0", "--port", "5000"]
