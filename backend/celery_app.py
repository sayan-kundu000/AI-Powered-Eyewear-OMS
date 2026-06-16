import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.tasks.celery_tasks import celery_app

if __name__ == "__main__":
    celery_app.start()
