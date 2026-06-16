from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LensInventory
from app.schemas import LensInventoryResponse, LensInventoryCreate
from app.api.auth import get_current_user, RoleChecker
from app.services.vendor_service import VendorService
from app.ai.models_registry import registry as ml_registry

router = APIRouter(prefix="/inventory", tags=["Inventory"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH", "CUSTOMER"])

@router.get("", response_model=List[LensInventoryResponse], dependencies=[Depends(role_staff_or_admin)])
def get_all_inventory(db: Session = Depends(get_db)):
    return db.query(LensInventory).all()

@router.get("/low-stock", response_model=List[LensInventoryResponse], dependencies=[Depends(role_staff_or_admin)])
def get_low_stock_inventory(db: Session = Depends(get_db)):
    # Lenses where (quantity - reserved_quantity) is less than 5
    return db.query(LensInventory).filter((LensInventory.quantity - LensInventory.reserved_quantity) < 5).all()

@router.get("/vendor-recommendations", dependencies=[Depends(role_staff_or_admin)])
def get_vendor_procurement_rankings(db: Session = Depends(get_db)):
    """
    Ranks supply vendors when raw lenses are unavailable.
    """
    return VendorService.get_recommendations(db)

@router.post("/reorder-needs", dependencies=[Depends(role_staff_or_admin)])
def predict_stock_reorder_needs(lens_id: int, db: Session = Depends(get_db)):
    """
    Apply ML to determine replenishment quantities and priorities.
    """
    lens = db.query(LensInventory).filter(LensInventory.id == lens_id).first()
    if not lens:
        raise HTTPException(status_code=404, detail="Lens record not found")
        
    # Features: [stock_quantity, sales_velocity_7d, lead_time_days, reorder_point, reserved_stock]
    # We compile features from the DB record:
    sales_velocity = 8  # Mock historical weekly sales velocity
    lead_time = 3       # Mock vendor replenishment lead time
    reorder_point = 8   # Threshold
    
    features = [
        float(lens.quantity),
        float(sales_velocity),
        float(lead_time),
        float(reorder_point),
        float(lens.reserved_quantity)
    ]
    
    prediction = ml_registry.predict_reorder_needs(db, features)
    return {
        "lens_id": lens.id,
        "lens_type": lens.lens_type,
        "current_quantity": lens.quantity,
        "reserved_quantity": lens.reserved_quantity,
        "forecasted_reorder": prediction
    }

from pydantic import BaseModel

class AddStockRequest(BaseModel):
    quantity: int

@router.post("", response_model=LensInventoryResponse, dependencies=[Depends(role_staff_or_admin)])
def create_inventory_item(lens_in: LensInventoryCreate, db: Session = Depends(get_db)):
    # Check if a lens with the same configuration already exists
    existing = db.query(LensInventory).filter(
        LensInventory.lens_type == lens_in.lens_type,
        LensInventory.index_value == lens_in.index_value,
        LensInventory.coating == lens_in.coating,
        LensInventory.power_sph == lens_in.power_sph,
        LensInventory.power_cyl == lens_in.power_cyl
    ).first()

    if existing:
        existing.quantity += lens_in.quantity
        if lens_in.thickness is not None:
            existing.thickness = lens_in.thickness
        if (existing.quantity - existing.reserved_quantity) > 0:
            existing.status = "IN_HOUSE"
        db.commit()
        db.refresh(existing)
        return existing

    new_item = LensInventory(
        lens_type=lens_in.lens_type,
        index_value=lens_in.index_value,
        coating=lens_in.coating,
        power_sph=lens_in.power_sph,
        power_cyl=lens_in.power_cyl,
        thickness=lens_in.thickness if lens_in.thickness is not None else 2.2,
        quantity=lens_in.quantity,
        reserved_quantity=0,
        status="IN_HOUSE" if lens_in.quantity > 0 else "OUT_OF_STOCK"
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.post("/{lens_id}/add-stock", response_model=LensInventoryResponse, dependencies=[Depends(role_staff_or_admin)])
def add_stock_to_item(lens_id: int, request: AddStockRequest, db: Session = Depends(get_db)):
    item = db.query(LensInventory).filter(LensInventory.id == lens_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lens inventory item not found")
    if request.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
    
    item.quantity += request.quantity
    if (item.quantity - item.reserved_quantity) > 0:
        item.status = "IN_HOUSE"
        
    db.commit()
    db.refresh(item)
    return item

