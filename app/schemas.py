# after data was already saved in the db, "Out"s will return the result and it's defined in the schema by defining what is allowed

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from .extensions import AllowedStatus

# USER
class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=5)
    full_name: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int 
    email: str
    full_name: str
    role: str
    created_at: datetime


# ORDER
class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=10) # greater than zero contraint


class OrderUpdate(BaseModel):
    quantity: int | None = Field(default=None, gt=0, le=10)
    status: AllowedStatus | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True) # lets pydantic to read directly from attributes sqlalchemy object
    # returns order from query using sqlalchemy -> FastAPI converts SQLAlchemy Order to OrderOut -> JSON
    id: int
    user_id: int
    product_id: int
    quantity: int
    status: str
    created_at: datetime

# Product
class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str | None
    price: float
    stock: int
    created_at: datetime