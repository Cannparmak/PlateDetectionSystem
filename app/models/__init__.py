# Tüm modelleri import et — SQLAlchemy relationship'lerin çözülmesi için gerekli
from app.models.user import User
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription import Subscription
from app.models.parking_session import ParkingSession
from app.models.parking_config import ParkingConfig

__all__ = [
    "User",
    "Customer",
    "Vehicle",
    "SubscriptionPlan",
    "Subscription",
    "ParkingSession",
    "ParkingConfig",
]
