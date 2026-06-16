import logging
from sqlalchemy.orm import Session
from app.models import LensInventory, Order, Notification, Frame
from app.services.event_bus import event_bus

logger = logging.getLogger("inventory_service")

class InventoryService:
    @staticmethod
    def check_lens_availability(
        db: Session, lens_type: str, sph: float, cyl: float, index_value: float, coating: str
    ) -> str:
        """
        Check if the lens is IN_HOUSE, VENDOR_REQUIRED, or OUT_OF_STOCK.
        """
        item = db.query(LensInventory).filter(
            LensInventory.lens_type == lens_type,
            LensInventory.power_sph == sph,
            LensInventory.power_cyl == cyl,
            LensInventory.index_value == index_value,
            LensInventory.coating == coating
        ).first()
        
        if item and (item.quantity - item.reserved_quantity) > 0:
            return "IN_HOUSE"
        elif item:
            return "VENDOR_REQUIRED"  # Item exists, but stock is 0 (must source from vendor)
        else:
            # Check if there is any general lens of this type/index at all
            general_exists = db.query(LensInventory).filter(
                LensInventory.lens_type == lens_type,
                LensInventory.index_value == index_value
            ).first()
            if general_exists:
                return "VENDOR_REQUIRED"
            return "OUT_OF_STOCK"

    @staticmethod
    def reserve_stock(db: Session, order: Order) -> bool:
        """
        Attempt to reserve Frame and Lens for an Order.
        If frame and lens are available in-house, mark status as RESERVED and decrement in-house quantities.
        Else, trigger vendor recommendation flow.
        """
        # 1. Reserve Frame
        frame_reserved = False
        if order.frame_id:
            frame = db.query(Frame).filter(Frame.id == order.frame_id).first()
            if frame and frame.stock_quantity > 0:
                frame.stock_quantity -= 1
                frame_reserved = True
                
        # 2. Reserve Lens
        lens_reserved = False
        if order.prescription:
            # We match using right eye parameters as proxy, or check both
            rx = order.prescription
            # Try to find matching lenses for both eyes
            lens_od = db.query(LensInventory).filter(
                LensInventory.lens_type == order.lens_type,
                LensInventory.power_sph == rx.sph_od,
                LensInventory.power_cyl == rx.cyl_od,
                LensInventory.index_value == order.lens_index
            ).first()
            
            lens_os = db.query(LensInventory).filter(
                LensInventory.lens_type == order.lens_type,
                LensInventory.power_sph == rx.sph_os,
                LensInventory.power_cyl == rx.cyl_os,
                LensInventory.index_value == order.lens_index
            ).first()
            
            # If both are available, reserve them
            if lens_od and (lens_od.quantity - lens_od.reserved_quantity) > 0 and \
               lens_os and (lens_os.quantity - lens_os.reserved_quantity) > 0:
                lens_od.reserved_quantity += 1
                lens_os.reserved_quantity += 1
                lens_reserved = True
                order.lens_stock_status = "IN_HOUSE"
                
                # Check for low-stock warnings after reservation
                InventoryService._check_replenish_alert(db, lens_od)
                InventoryService._check_replenish_alert(db, lens_os)
            else:
                order.lens_stock_status = "VENDOR_REQUIRED"
        else:
            order.lens_stock_status = "PENDING_PRESCRIPTION"
        
        db.commit()
        
        # Publish inventory reservation results
        event_bus.publish("InventoryReserved", {
            "order_id": order.id,
            "frame_reserved": frame_reserved,
            "lens_reserved": lens_reserved
        })
        
        return frame_reserved and lens_reserved

    @staticmethod
    def deduct_stock(db: Session, order: Order):
        """
        Deduct the reserved lens quantities when the order is shipped.
        """
        if order.prescription:
            rx = order.prescription
            lens_od = db.query(LensInventory).filter(
                LensInventory.lens_type == order.lens_type,
                LensInventory.power_sph == rx.sph_od,
                LensInventory.power_cyl == rx.cyl_od,
                LensInventory.index_value == order.lens_index
            ).first()
            
            lens_os = db.query(LensInventory).filter(
                LensInventory.lens_type == order.lens_type,
                LensInventory.power_sph == rx.sph_os,
                LensInventory.power_cyl == rx.cyl_os,
                LensInventory.index_value == order.lens_index
            ).first()
            
            if lens_od and lens_od.reserved_quantity > 0:
                lens_od.reserved_quantity -= 1
                if lens_od.quantity > 0:
                    lens_od.quantity -= 1
                    
            if lens_os and lens_os.reserved_quantity > 0:
                lens_os.reserved_quantity -= 1
                if lens_os.quantity > 0:
                    lens_os.quantity -= 1
                    
        db.commit()

    @staticmethod
    def _check_replenish_alert(db: Session, lens: LensInventory):
        """
        If inventory falls below threshold (e.g. 5 units), trigger an auto replenish alert.
        """
        threshold = 5
        available = lens.quantity - lens.reserved_quantity
        if available < threshold:
            alert_content = (
                f"REPLENISHMENT ALERT: Lens type '{lens.lens_type}' (Index: {lens.index_value}, "
                f"SPH: {lens.power_sph}, CYL: {lens.power_cyl}) is low in stock. "
                f"Available: {available} units."
            )
            # Log notification
            notification = Notification(
                channel="EMAIL",
                recipient="inventory-manager@eyewearoms.com",
                content=alert_content,
                status="PENDING"
            )
            db.add(notification)
            db.commit()
            logger.info(f"Replenishment alert created for Lens ID: {lens.id}")
