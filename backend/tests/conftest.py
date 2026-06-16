import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.config import settings

# Test database engine using an in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Setup tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_celery_tasks():
    with patch("app.tasks.celery_tasks.send_email_notification_task.delay") as mock_email, \
         patch("app.tasks.celery_tasks.send_whatsapp_notification_task.delay") as mock_wa:
        yield mock_email, mock_wa
