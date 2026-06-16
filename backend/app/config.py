import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Eyewear OMS"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database Settings
    # Defaulting to a local SQLite database for easy development/testing, but production uses PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./eyewear_oms.db")
    
    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_signing_key_change_me_in_production_1234567890")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for development
    
    # Razorpay Settings (Mock details by default)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mockkeyid123")
    RAZORPAY_SECRET: str = os.getenv("RAZORPAY_SECRET", "mocksecretkey1234567890")
    
    # Communications (SMTP / Twilio)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "notifications@eyewearoms.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "mockpassword123")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@eyewearoms.com")
    
    # Twilio API
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "ACmockaccountsid123456")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "mockauthtoken12345678")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "+1234567890")
    
    # File Storage (AWS S3 / Cloudinary)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "mockaccesskey")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "mocksecretkey")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "eyewear-oms-media")
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "")
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [origin.strip() for origin in os.getenv("BACKEND_CORS_ORIGINS", "*").split(",") if origin.strip()]
    
    # AI/ML Model Settings
    MODEL_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
    
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", env_file_encoding="utf-8")

    def __init__(self, **values):
        super().__init__(**values)
        if self.ENVIRONMENT.lower() == "production":
            # 1. Enforce JWT Secret changes
            if "change_me" in self.JWT_SECRET or self.JWT_SECRET == "super_secret_jwt_signing_key_change_me_in_production_1234567890":
                raise ValueError("Security Breach: JWT_SECRET must be securely changed in production environment!")
            
            # 2. Enforce Database URL check (Postgres only in production)
            if not (self.DATABASE_URL.startswith("postgresql") or self.DATABASE_URL.startswith("postgres")):
                raise ValueError("Configuration Error: Production environment requires a PostgreSQL database connection URL!")
                
            # 3. Enforce SMTP Password rotation
            if self.SMTP_PASSWORD == "simyteigjdagdqpc" or self.SMTP_PASSWORD == "mockpassword123":
                raise ValueError("Security Breach: Hardcoded/leaked SMTP credentials detected. You must rotate and provide production credentials!")

settings = Settings()

# Ensure model directory exists
os.makedirs(settings.MODEL_DIR, exist_ok=True)
