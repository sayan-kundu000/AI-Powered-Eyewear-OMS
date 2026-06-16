import sys
import os
import datetime
import random

# Add parent directories to Python Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import User, Role, Store, Customer, Frame, LensInventory, Coating, Order, VendorPerformance
from app.api.auth import get_password_hash

def seed_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    print("Seeding database...")
    
    # 1. Seed Users and Roles
    admin_pw = get_password_hash("password123")
    admin_user = db.query(User).filter(User.email == "admin@eyewearoms.com").first()
    if not admin_user:
        admin_user = User(
            email="admin@eyewearoms.com",
            hashed_password=admin_pw,
            full_name="Principal Architect Admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Add roles
        db.add(Role(user_id=admin_user.id, role_name="ADMIN"))
        db.add(Role(user_id=admin_user.id, role_name="STORE_STAFF"))
        db.add(Role(user_id=admin_user.id, role_name="LAB_TECH"))
        db.commit()
        print("Admin user seeded.")
        
    lab_pw = get_password_hash("password123")
    lab_user = db.query(User).filter(User.email == "lab@eyewearoms.com").first()
    if not lab_user:
        lab_user = User(
            email="lab@eyewearoms.com",
            hashed_password=lab_pw,
            full_name="Lead Lab Technician",
            is_active=True
        )
        db.add(lab_user)
        db.commit()
        db.refresh(lab_user)
        
        # Add roles
        db.add(Role(user_id=lab_user.id, role_name="LAB_TECH"))
        db.commit()
        print("Lab technician seeded.")

    # 2. Seed Stores
    stores_data = [
        {"name": "Vasanthnagar Flagship", "location": "Bangalore"},
        {"name": "Colaba Retail Store", "location": "Mumbai"},
        {"name": "Connaught Place Outlet", "location": "Delhi"},
        {"name": "Nungambakkam Hub", "location": "Chennai"},
        {"name": "Salt Lake Gallery", "location": "Kolkata"},
        {"name": "Hitech City Shop", "location": "Hyderabad"},
        {"name": "Deccan Gymkhana Store", "location": "Pune"},
        {"name": "Lal Darwaza Outlet", "location": "Ahmedabad"},
        {"name": "Hazratganj Store", "location": "Lucknow"},
        {"name": "Sector 17 Gallery", "location": "Chandigarh"}
    ]
    
    stores = []
    for s_item in stores_data:
        store = db.query(Store).filter(Store.name == s_item["name"]).first()
        if not store:
            store = Store(name=s_item["name"], location=s_item["location"], contact_number="9876543210")
            db.add(store)
            db.commit()
            db.refresh(store)
        stores.append(store)
    print(f"Seeded {len(stores)} stores.")

    # 3. Seed Coatings
    coatings_data = [
        {"name": "Anti-Reflective Coating", "description": "Reduces glare, visual stress, and reflections", "extra_cost": 500.0, "lead_time_days": 1},
        {"name": "Blue Cut / Digital Block", "description": "Blocks harmful high-energy blue light from screens", "extra_cost": 800.0, "lead_time_days": 1},
        {"name": "Scratch-Resistant Shield", "description": "Hard protective layer to minimize micro-scratches", "extra_cost": 300.0, "lead_time_days": 0},
        {"name": "Photochromic Transition", "description": "Darkens in response to UV rays outside", "extra_cost": 1500.0, "lead_time_days": 2}
    ]
    
    coatings = []
    for c_item in coatings_data:
        coating = db.query(Coating).filter(Coating.name == c_item["name"]).first()
        if not coating:
            coating = Coating(**c_item)
            db.add(coating)
            db.commit()
            db.refresh(coating)
        coatings.append(coating)
    print(f"Seeded {len(coatings)} coatings.")

    # 4. Seed Frames
    frames_data = [
        {"name": "Titan Wayfarer Black", "model_number": "FRM-TIT-01", "brand": "Titan", "color": "Matte Black", "size": "Medium", "cost": 800.0, "price": 1999.0, "stock_quantity": 50},
        {"name": "RayBan Aviator Gold", "model_number": "FRM-RAY-02", "brand": "RayBan", "color": "Gold", "size": "Large", "cost": 2500.0, "price": 5999.0, "stock_quantity": 30},
        {"name": "Oakley Rectangular Blue", "model_number": "FRM-OAK-03", "brand": "Oakley", "color": "Navy Blue", "size": "Medium", "cost": 1800.0, "price": 3999.0, "stock_quantity": 25},
        {"name": "Fastrack Round Silver", "model_number": "FRM-FAS-04", "brand": "Fastrack", "color": "Sleek Silver", "size": "Small", "cost": 400.0, "price": 999.0, "stock_quantity": 40}
    ]
    
    frames = []
    for f_item in frames_data:
        frame = db.query(Frame).filter(Frame.model_number == f_item["model_number"]).first()
        if not frame:
            frame = Frame(**f_item)
            db.add(frame)
            db.commit()
            db.refresh(frame)
        frames.append(frame)
    print(f"Seeded {len(frames)} frames.")

    # 5. Seed Vendor Performance
    vendors_data = [
        {"vendor_name": "Essilor India Manufacturing", "cost": 450.0, "reliability_score": 98.5, "sla_days": 3, "performance_history_score": 96.0},
        {"vendor_name": "Carl Zeiss Sourcing Asia", "cost": 650.0, "reliability_score": 99.2, "sla_days": 4, "performance_history_score": 98.0},
        {"vendor_name": "Hoya Vision Logistics", "cost": 380.0, "reliability_score": 92.0, "sla_days": 2, "performance_history_score": 88.0}
    ]
    
    for v_item in vendors_data:
        v = db.query(VendorPerformance).filter(VendorPerformance.vendor_name == v_item["vendor_name"]).first()
        if not v:
            db.add(VendorPerformance(**v_item))
    db.commit()
    print("Seeded vendors performance.")

    # 6. Seed Customers
    customers = []
    categories = ["Bronze", "Silver", "Gold", "Platinum"]
    for i in range(1, 101):
        c_email = f"customer{i}@gmail.com"
        customer = db.query(Customer).filter(Customer.email == c_email).first()
        if not customer:
            spending = random.choice([0.0, 1500.0, 4500.0, 12000.0, 25000.0])
            freq = 0 if spending == 0.0 else int(spending / 5000.0) + 1
            clv_cat = categories[min(3, freq)]
            
            customer = Customer(
                first_name=f"Customer{i}",
                last_name=f"Lastname{i}",
                email=c_email,
                phone=f"990000{i:04d}",
                clv_category=clv_cat,
                clv_score=float(spending / 250.0),
                purchase_frequency=freq,
                total_spent=spending
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
        customers.append(customer)
    print(f"Seeded {len(customers)} customers.")

    # 7. Seed Lens Inventory (grid of standard lens prescriptions)
    lens_types = ["Single Vision", "Progressive", "Blue Cut"]
    indexes = [1.56, 1.61, 1.67, 1.74]
    coatings_list = ["Anti-Reflective", "Blue Cut", "Photochromic", "Scratch-Resistant"]
    
    # We populate basic spheres from -4.00 to +4.00 and cylinder from -2.00 to 0.00
    db_items_count = db.query(LensInventory).count()
    if db_items_count < 100:
        lenses_to_insert = []
        for l_type in lens_types:
            for idx in indexes:
                for coat in coatings_list:
                    for sph in [-2.00, -1.00, 0.00, 1.00, 2.00]:
                        for cyl in [-1.00, 0.00]:
                            lenses_to_insert.append(
                                LensInventory(
                                    lens_type=l_type,
                                    index_value=idx,
                                    coating=coat,
                                    power_sph=sph,
                                    power_cyl=cyl,
                                    thickness=2.2,
                                    quantity=25,
                                    reserved_quantity=0,
                                    status="IN_HOUSE"
                                )
                            )
        db.bulk_save_objects(lenses_to_insert)
        db.commit()
        print("Bulk lens inventory grids generated.")

    # 8. Seed Orders (500 historical orders across dates)
    order_count = db.query(Order).count()
    if order_count < 100:
        print("Generating 500 simulated historic orders...")
        statuses_distribution = [
            "DELIVERED", "DELIVERED", "DELIVERED", "DELIVERED", # 80% Delivered
            "SHIPPED", "OUT_FOR_DELIVERY", "IN_LAB", "ORDER_PLACED", "CANCELLED", "QC_FAILED"
        ]
        
        orders_to_insert = []
        for i in range(1, 501):
            cust = random.choice(customers)
            store = random.choice(stores)
            frame = random.choice(frames)
            coating = random.choice(coatings)
            lens = random.choice(lens_types)
            status_val = random.choice(statuses_distribution)
            
            # SLA and risk
            sla_days = 2 if "single" in lens.lower() else 5
            remaining = float(random.choice([24, 48, -12, -4, 72]))
            risk = "High" if remaining < 0 else ("Medium" if remaining < 12 else "Low")
            
            timestamp = (datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 90)))
            
            orders_to_insert.append(
                Order(
                    order_number=f"ORD-SIM-{timestamp.strftime('%y%m%d%H%M')}-{i:03d}",
                    customer_id=cust.id,
                    store_id=store.id,
                    frame_id=frame.id,
                    lens_type=lens,
                    lens_index=1.61,
                    coating_id=coating.id,
                    payment_status="PAID",
                    total_amount=frame.price + coating.extra_cost + 1000.0,
                    current_status=status_val,
                    current_sla_days=sla_days,
                    remaining_tat_hours=remaining,
                    risk_score=risk,
                    created_at=timestamp,
                    updated_at=timestamp
                )
            )
        db.bulk_save_objects(orders_to_insert)
        db.commit()
        print("500 Orders seeded successfully.")
        
    db.close()
    print("Database seeding finished!")

if __name__ == "__main__":
    seed_database()
