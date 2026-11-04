from enum import Enum

class AllowedRole(str, Enum):
    customer = "customer"
    member = "member"
    admin = "admin"

class AllowedStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"