from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    roles: List[str] = []

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "CUSTOMER"

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    roles: List[str] = []

    class Config:
        from_attributes = True

# Customer Schemas
class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str

class CustomerResponse(CustomerCreate):
    id: int
    clv_category: str
    clv_score: float
    purchase_frequency: int
    total_spent: float
    created_at: datetime

    class Config:
        from_attributes = True

# Prescription Schemas
class PrescriptionCreate(BaseModel):
    customer_id: int
    sph_od: float
    cyl_od: float = 0.0
    axis_od: int = 0
    add_od: float = 0.0
    sph_os: float
    cyl_os: float = 0.0
    axis_os: int = 0
    add_os: float = 0.0
    pd: float

class PrescriptionResponse(PrescriptionCreate):
    id: int
    pdf_url: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    is_validated: bool
    verified_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Frame Schemas
class FrameResponse(BaseModel):
    id: int
    name: str
    model_number: str
    brand: str
    color: str
    size: str
    cost: float
    price: float
    stock_quantity: int
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

# Lens Inventory Schemas
class LensInventoryCreate(BaseModel):
    lens_type: str
    index_value: float
    coating: str
    power_sph: float
    power_cyl: float
    thickness: Optional[float] = None
    quantity: int

class LensInventoryResponse(LensInventoryCreate):
    id: int
    reserved_quantity: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Coating Schemas
class CoatingResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    extra_cost: float
    lead_time_days: int

    class Config:
        from_attributes = True

# Order Schemas
class OrderCreate(BaseModel):
    customer_id: int
    store_id: int
    prescription_id: Optional[int] = None
    frame_id: Optional[int] = None
    lens_type: str
    lens_index: float
    coating_id: Optional[int] = None
    total_amount: float

class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    store_id: int
    prescription_id: Optional[int] = None
    frame_id: Optional[int] = None
    lens_type: str
    lens_index: float
    coating_id: Optional[int] = None
    payment_status: str
    total_amount: float
    current_status: str
    current_sla_days: int
    remaining_tat_hours: float
    breach_risk_prob: float
    risk_score: str
    lens_stock_status: Optional[str] = "PENDING"
    delay_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

# Payment Schemas
class PaymentCreate(BaseModel):
    order_id: int
    amount: float

class PaymentVerify(BaseModel):
    order_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_gateway: str
    transaction_id: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Shipment Schemas
class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    courier_name: str
    tracking_number: Optional[str] = None
    status: str
    origin: str
    destination: str
    estimated_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    weather_condition: str
    shipping_cost: float
    created_at: datetime

    class Config:
        from_attributes = True

# QC Schemas
class QCLogResponse(BaseModel):
    id: int
    order_id: int
    image_url: Optional[str] = None
    qc_score: float
    surface_defect_score: float
    alignment_score: float
    recommendation: str
    inspector_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class QCVerifyResult(BaseModel):
    qc_score: float
    surface_defect_score: float
    alignment_score: float
    recommendation: str
    details: Dict[str, Any]

# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    channel: str
    recipient: str
    content: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Analytics & Dashboard Schemas
class ActiveOrdersOverview(BaseModel):
    total_active: int
    completed: int
    delayed: int
    breached: int

class DashboardData(BaseModel):
    overview: ActiveOrdersOverview
    daily_orders: List[Dict[str, Any]]
    tat_trends: List[Dict[str, Any]]
    qc_failure_rate: float
    store_performance: List[Dict[str, Any]]
    lens_demand_heatmap: List[Dict[str, Any]]

# Chat Schemas
class ChatQuery(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None

# Embedding Schemas
class EmbeddingGenerateRequest(BaseModel):
    sph: float
    cyl: float
    axis: int
    add_val: float

class EmbeddingSearchRequest(BaseModel):
    embedding: List[float]
    top_k: int = 5
    metric: str = "cosine"  # cosine or euclidean
