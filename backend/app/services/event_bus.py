import json
import logging
import redis
from app.config import settings

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Could not connect to Redis for EventBus: {e}. Event logging will fallback to standard loggers.")

    def publish(self, event_name: str, payload: dict):
        """
        Publish an event to the Redis Stream.
        Events: OrderCreated, InventoryReserved, PrescriptionProcessed, QCCompleted, ShipmentCreated, OrderDelivered.
        """
        event_data = {
            "event": event_name,
            "payload": json.dumps(payload),
            "timestamp": datetime_str()
        }
        
        if self.redis_client:
            try:
                # Write to stream 'eyewear_events'
                self.redis_client.xadd("eyewear_events", event_data)
                # Also publish to pubsub channel for real-time WebSocket dashboard sync
                self.redis_client.publish("dashboard_updates", json.dumps(event_data))
                logger.info(f"Published event {event_name} to Redis Streams.")
            except Exception as e:
                logger.error(f"Failed to publish event {event_name} to Redis: {e}")
        else:
            logger.info(f"[Fallback Log] Event: {event_name} | Payload: {payload}")

def datetime_str():
    import datetime
    return datetime.datetime.utcnow().isoformat()

event_bus = EventBus()
