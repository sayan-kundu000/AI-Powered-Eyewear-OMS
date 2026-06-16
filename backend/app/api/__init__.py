from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.orders import router as orders_router
from app.api.inventory import router as inventory_router
from app.api.prescription import router as prescription_router
from app.api.ocr import router as ocr_router
from app.api.prediction import router as prediction_router
from app.api.payments import router as payments_router
from app.api.notifications import router as notifications_router
from app.api.analytics import router as analytics_router
from app.api.chat import router as chat_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(orders_router)
api_router.include_router(inventory_router)
api_router.include_router(prescription_router)
api_router.include_router(ocr_router)
api_router.include_router(prediction_router)
api_router.include_router(payments_router)
api_router.include_router(notifications_router)
api_router.include_router(analytics_router)
api_router.include_router(chat_router)
