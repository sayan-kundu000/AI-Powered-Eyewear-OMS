import pytest
from sqlalchemy.orm import Session
from app.models import LensInventory, Customer, Store, Prescription, Order, Coating
from app.services.inventory_service import InventoryService
from fastapi import HTTPException

def test_add_inventory_item(db_session: Session):
    # Try adding a new inventory item
    # Initially we have no inventory in the database since it resets for the function scope
    assert db_session.query(LensInventory).count() == 0
    
    # Let's mock a LensInventoryCreate request content
    from app.schemas import LensInventoryCreate
    lens_in = LensInventoryCreate(
        lens_type="Single Vision",
        index_value=1.56,
        coating="Anti-Reflective",
        power_sph=-2.00,
        power_cyl=-1.00,
        thickness=2.2,
        quantity=15
    )
    
    # We test create_inventory_item functionality
    from app.api.inventory import create_inventory_item
    item = create_inventory_item(lens_in, db_session)
    
    assert item.id is not None
    assert item.quantity == 15
    assert item.status == "IN_HOUSE"
    
    # If we add it again (same specs), it should increase the quantity
    lens_in_2 = LensInventoryCreate(
        lens_type="Single Vision",
        index_value=1.56,
        coating="Anti-Reflective",
        power_sph=-2.00,
        power_cyl=-1.00,
        thickness=2.2,
        quantity=10
    )
    item_updated = create_inventory_item(lens_in_2, db_session)
    assert item_updated.id == item.id
    assert item_updated.quantity == 25

def test_add_stock_to_item(db_session: Session):
    # Add an item to start with
    item = LensInventory(
        lens_type="Progressive",
        index_value=1.67,
        coating="Blue Cut",
        power_sph=1.00,
        power_cyl=0.00,
        thickness=2.5,
        quantity=5,
        reserved_quantity=0,
        status="IN_HOUSE"
    )
    db_session.add(item)
    db_session.commit()
    
    from app.api.inventory import add_stock_to_item, AddStockRequest
    req = AddStockRequest(quantity=12)
    updated_item = add_stock_to_item(item.id, req, db_session)
    
    assert updated_item.quantity == 17
    assert updated_item.status == "IN_HOUSE"

def test_order_placement_sla_reduction(db_session: Session):
    # Setup customer, store, coating, and prescription
    cust = Customer(first_name="Alice", last_name="Smith", email="alice@test.com", phone="99999")
    store = Store(name="Vasanthnagar Flagship", location="Bangalore")
    coating = Coating(name="Anti-Reflective Coating", extra_cost=500.0, lead_time_days=1)
    db_session.add_all([cust, store, coating])
    db_session.commit()
    
    rx = Prescription(
        customer_id=cust.id,
        sph_od=-2.00,
        cyl_od=-1.00,
        axis_od=180,
        sph_os=-2.00,
        cyl_os=-1.00,
        axis_os=180,
        pd=62.0,
        is_validated=True
    )
    db_session.add(rx)
    db_session.commit()
    
    # 1. Place order when lenses are NOT in house
    # We should have VENDOR_REQUIRED stock status and default SLA
    from app.schemas import OrderCreate
    from app.api.orders import create_new_order
    from app.models import User
    
    # Mock current user
    mock_user = User(email="staff@test.com", hashed_password="pw", full_name="Staff User")
    db_session.add(mock_user)
    db_session.commit()
    
    order_in_out_of_stock = OrderCreate(
        customer_id=cust.id,
        store_id=store.id,
        prescription_id=rx.id,
        frame_id=None,
        lens_type="Single Vision",
        lens_index=1.56,
        coating_id=coating.id,
        total_amount=1500.0
    )
    
    order1 = create_new_order(order_in_out_of_stock, db_session, mock_user)
    assert order1.lens_stock_status == "VENDOR_REQUIRED"
    assert order1.current_sla_days == 2  # Single Vision default is 2
    assert pytest.approx(order1.remaining_tat_hours, abs=0.2) == 48.0
    
    # 2. Add matching lenses to inventory so they are IN HOUSE
    lens_od = LensInventory(
        lens_type="Single Vision",
        index_value=1.56,
        coating="Anti-Reflective Coating",
        power_sph=-2.00,
        power_cyl=-1.00,
        thickness=2.2,
        quantity=10,
        reserved_quantity=0,
        status="IN_HOUSE"
    )
    lens_os = LensInventory(
        lens_type="Single Vision",
        index_value=1.56,
        coating="Anti-Reflective Coating",
        power_sph=-2.00,
        power_cyl=-1.00,
        thickness=2.2,
        quantity=10,
        reserved_quantity=0,
        status="IN_HOUSE"
    )
    db_session.add_all([lens_od, lens_os])
    db_session.commit()
    
    # Place order again with lenses available in house
    order_in_in_house = OrderCreate(
        customer_id=cust.id,
        store_id=store.id,
        prescription_id=rx.id,
        frame_id=None,
        lens_type="Single Vision",
        lens_index=1.56,
        coating_id=coating.id,
        total_amount=1500.0
    )
    
    order2 = create_new_order(order_in_in_house, db_session, mock_user)
    assert order2.lens_stock_status == "IN_HOUSE"
    assert order2.current_sla_days == 1  # Shortened SLA (ASAP delivery)
    assert pytest.approx(order2.remaining_tat_hours, abs=0.2) == 24.0
