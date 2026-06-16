import os
import asyncio
import json
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import engine, Base
from app.api import api_router

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

if settings.ENVIRONMENT.lower() == "production":
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("main")

# Auto-create tables (Alembic can also handle migrations in production)
try:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    
    # Ensure delay_reason column exists (self-healing migration)
    with engine.begin() as conn:
        from sqlalchemy import text
        try:
            conn.execute(text("SELECT delay_reason FROM orders LIMIT 1"))
        except Exception:
            logger.info("delay_reason column not found in orders table. Adding it...")
            try:
                conn.execute(text("ALTER TABLE orders ADD COLUMN delay_reason TEXT"))
                logger.info("delay_reason column added successfully.")
            except Exception as ex:
                logger.error(f"Failed to add delay_reason column: {ex}")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready AI-Powered Order Management System (OMS) for Eyewear",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist and mount them
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(os.path.join(static_dir, "prescriptions"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "qc"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["System"])
def root_endpoint():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs",
        "timestamp": datetime_str()
    }

@app.get("/health", tags=["System"])
def health_endpoint():
    db_ok = False
    redis_ok = False
    details = {}
    
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
        details["database"] = "connected"
    except Exception as e:
        logger.error(f"Health check database connection failed: {e}")
        details["database"] = f"unreachable: {str(e)}"
        
    try:
        import redis
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        redis_ok = True
        details["redis"] = "connected"
    except Exception as e:
        logger.error(f"Health check Redis connection failed: {e}")
        details["redis"] = f"unreachable: {str(e)}"

    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=500,
            detail={"status": "unhealthy", **details, "timestamp": datetime_str()}
        )
        
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "timestamp": datetime_str()
    }

def datetime_str():
    import datetime
    return datetime.datetime.utcnow().isoformat()

# ====================================================
# WEBSOCKET REAL-TIME SYNC MANAGER
# ====================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        logger.info(f"Broadcasting message to {len(self.active_connections)} clients: {message}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending WebSocket frame: {e}. Cleaning up connection.")
                # Connection is likely dead, let's remove it later
                
manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection, handle client pings
            data = await websocket.receive_text()
            # If clients send message, respond or ignore
            await websocket.send_json({"event": "pong", "message": "alive"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        manager.disconnect(websocket)

# Background Task to listen to Redis PubSub updates and broadcast them to WebSockets
@app.on_event("startup")
async def startup_event():
    # Start Redis listener task
    loop = asyncio.get_event_loop()
    loop.create_task(listen_to_redis_channel())

async def listen_to_redis_channel():
    import redis
    r = None
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        pubsub.subscribe("dashboard_updates")
        logger.info("Successfully subscribed to Redis PubSub channel 'dashboard_updates'.")
        
        while True:
            # Check message asynchronously
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                try:
                    event_data = json.loads(message["data"])
                    await manager.broadcast(event_data)
                except Exception as e:
                    logger.error(f"Error broadcasting event from Redis PubSub: {e}")
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.warning(f"Redis PubSub listener failed to start: {e}. WebSockets will fall back to local triggers only.")
