import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Numeric
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    roles = relationship("Role", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_name = Column(String, nullable=False)  # ADMIN, LAB_TECH, STORE_STAFF, CUSTOMER
    
    user = relationship("User", back_populates="roles")

class Store(Base):
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    contact_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    orders = relationship("Order", back_populates="store")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    
    # CLV fields
    clv_category = Column(String, default="Bronze")  # Bronze, Silver, Gold, Platinum
    clv_score = Column(Float, default=0.0)
    purchase_frequency = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    orders = relationship("Order", back_populates="customer")
    prescriptions = relationship("Prescription", back_populates="customer")

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Right Eye (Oculus Dexter - OD)
    sph_od = Column(Float, nullable=False)
    cyl_od = Column(Float, default=0.0)
    axis_od = Column(Integer, default=0)
    add_od = Column(Float, default=0.0)
    
    # Left Eye (Oculus Sinister - OS)
    sph_os = Column(Float, nullable=False)
    cyl_os = Column(Float, default=0.0)
    axis_os = Column(Integer, default=0)
    add_os = Column(Float, default=0.0)
    
    pd = Column(Float, nullable=False)  # Pupillary Distance (shared or average)
    
    pdf_url = Column(String, nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    
    # For embedding similarity (stored as JSON string of float list)
    embedding = Column(Text, nullable=True) 
    
    is_validated = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    customer = relationship("Customer", back_populates="prescriptions")
    orders = relationship("Order", back_populates="prescription")

class Frame(Base):
    __tablename__ = "frames"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    model_number = Column(String, unique=True, nullable=False)
    brand = Column(String, nullable=False)
    color = Column(String, nullable=False)
    size = Column(String, nullable=False)
    cost = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    
    orders = relationship("Order", back_populates="frame")

class LensInventory(Base):
    __tablename__ = "lens_inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    lens_type = Column(String, nullable=False)  # Single Vision, Progressive, Blue Cut, etc.
    index_value = Column(Float, nullable=False)   # 1.56, 1.61, 1.67, 1.74
    coating = Column(String, nullable=False)      # Anti-Reflective, Blue Cut, Photochromic, Scratch-Resistant
    power_sph = Column(Float, nullable=False)
    power_cyl = Column(Float, nullable=False)
    thickness = Column(Float, nullable=True)
    quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    status = Column(String, default="IN_HOUSE")   # IN_HOUSE, OUT_OF_STOCK, VENDOR_REQUIRED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Coating(Base):
    __tablename__ = "coatings"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    extra_cost = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=0)
    
    orders = relationship("Order", back_populates="coating")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True, index=True)
    frame_id = Column(Integer, ForeignKey("frames.id"), nullable=True, index=True)
    
    lens_type = Column(String, nullable=False)
    lens_index = Column(Float, nullable=False)
    coating_id = Column(Integer, ForeignKey("coatings.id"), nullable=True)
    
    payment_status = Column(String, default="PENDING")  # PENDING, PAID, FAILED, REFUNDED
    total_amount = Column(Float, nullable=False)
    
    # FSM status
    current_status = Column(String, default="ORDER_PLACED", index=True) 
    
    # SLA parameters
    current_sla_days = Column(Integer, default=3)
    remaining_tat_hours = Column(Float, default=72.0)
    breach_risk_prob = Column(Float, default=0.0)
    risk_score = Column(String, default="Low")  # Low, Medium, High
    lens_stock_status = Column(String, default="PENDING")  # PENDING, IN_HOUSE, VENDOR_REQUIRED
    delay_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    customer = relationship("Customer", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    prescription = relationship("Prescription", back_populates="orders")
    frame = relationship("Frame", back_populates="orders")
    coating = relationship("Coating", back_populates="orders")
    
    payments = relationship("Payment", back_populates="order")
    shipments = relationship("Shipment", back_populates="order")
    sla_history = relationship("SLAHistory", back_populates="order")
    qc_logs = relationship("QCLog", back_populates="order")
    prediction_logs = relationship("PredictionLog", back_populates="order")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_gateway = Column(String, default="Razorpay")
    transaction_id = Column(String, unique=True, nullable=True)
    status = Column(String, default="PENDING", index=True)  # PENDING, SUCCESS, FAILED, REFUNDED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    order = relationship("Order", back_populates="payments")

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    courier_name = Column(String, nullable=False)
    tracking_number = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, SHIPPED, OUT_FOR_DELIVERY, DELIVERED, RETURNED
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    estimated_delivery_date = Column(DateTime, nullable=True)
    actual_delivery_date = Column(DateTime, nullable=True)
    weather_condition = Column(String, default="Sunny")
    shipping_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    order = relationship("Order", back_populates="shipments")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    channel = Column(String, nullable=False)  # EMAIL, WHATSAPP
    recipient = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, SENT, FAILED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # INSERT, UPDATE, DELETE
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")

class SLAHistory(Base):
    __tablename__ = "sla_history"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    stage = Column(String, nullable=False)  # e.g., CUTTING, COATING
    entered_at = Column(DateTime, default=datetime.datetime.utcnow)
    exited_at = Column(DateTime, nullable=True)
    tat_hours = Column(Float, nullable=True)
    sla_limit_hours = Column(Float, nullable=False)
    status = Column(String, default="ON_TIME")  # ON_TIME, BREACHED
    
    order = relationship("Order", back_populates="sla_history")

class QCLog(Base):
    __tablename__ = "qc_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    image_url = Column(String, nullable=True)
    qc_score = Column(Float, nullable=False)
    surface_defect_score = Column(Float, nullable=False)
    alignment_score = Column(Float, nullable=False)
    recommendation = Column(String, nullable=False)  # PASS, FAIL
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    order = relationship("Order", back_populates="qc_logs")

class Reorder(Base):
    __tablename__ = "reorders"
    
    id = Column(Integer, primary_key=True, index=True)
    original_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    new_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    model_name = Column(String, nullable=False)
    prediction_type = Column(String, nullable=False)  # SLA_BREACH, DEMAND_FORECAST, CLV_SCORE, VENDOR_REC, SHORTAGE
    inputs = Column(Text, nullable=True)  # JSON serialized input dictionary
    outputs = Column(Text, nullable=True)  # JSON serialized output dictionary
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    order = relationship("Order", back_populates="prediction_logs")

class VendorPerformance(Base):
    __tablename__ = "vendor_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, unique=True, nullable=False)
    cost = Column(Float, nullable=False)
    reliability_score = Column(Float, default=100.0)  # 0 to 100
    sla_days = Column(Integer, nullable=False)
    performance_history_score = Column(Float, default=100.0)
