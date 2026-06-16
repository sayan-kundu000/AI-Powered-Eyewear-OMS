#!/bin/bash
set -e

echo "Starting Celery background worker process..."
celery -A celery_app.celery_app worker --loglevel=info &

echo "Starting FastAPI Uvicorn server process..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
