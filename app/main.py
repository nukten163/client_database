# --- imports
from fastapi import FastAPI, HTTPException, Response, Depends, Query, status
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm)
from sqlalchemy.orm import Session
from .auth import verify_password, create_access_token, decode_access_token, hash_password
from .extensions import AllowedStatus

from .database import get_db
from .models import Order, User, Product
from .schemas import *

# --- setup
app = FastAPI(title="Orders API", version="0.1.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl to endpoint POST("/token")

# --- auth
@app.post("/register", response_model=UserOut, status_code=201)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    """
    Registers a new user an adds them into the database

    Args:
        payload (UserCreate): Data in the format of UserCreate
        db (Session): Current session

    Returns:
        User: A User object

    Raises:
        HTTPException: 409 if email has already been registered
    """
    
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@app.post("/token")
def  login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)) -> dict:
    """
    Checks if the email and password match and generates an access token

    Args:
        form_data (OAuth2PasswordRequestForm): Login form data; `username` holds
            the user's email, `password` the plain-text password
        db (Session): Current session

    Returns:
        dict: `access_token` (signed JWT) and `token_type` ("bearer")

    Raises:
        HTTPException: 401 if the email doesn't exist or the password is incorrect
    """
    user = (
        db.query(User)
        .filter(User.email == form_data.username)
        .first()
    )

    if user is None or not verify_password(
        form_data.password,
        user.hashed_password,):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer"
    }

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)) -> User:
    """
    Checks if the token is valid and if the user exists to return User object

    Args:
        token (str): Access token from the "Authorization: Bearer" header
        db (Session): Current session

    Returns:
        User: Logged in user from the users table

    Raises:
        HTTPException: 401 if token is invalid or expired, or if user doesn't exist
    """

    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exist")

    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Checks if the current user's role is admin

    Args:
        current_user (User): Logged in user to derive the role from

    Returns:
        User: Current user if the role is admin

    Raises:
        HTTPException: 403 (Forbidden) if current user's role is not admin
    """

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user

@app.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns an User object with current_user's information

    Args:
        current_user (User): Currently logged in user

    Returns:
        User: Current user's information
    """

    return current_user

# --- Product Read-only
@app.get("/products", response_model=list[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0), # ?skip=1
    limit: int = Query(10, ge=1, le=20),) -> list[Product]:
    """
    Returns paginated list of products ordered by ID

    Args:
        db (Session): Current session
        skip (int): Number of products to skip (offset)
        limit (int): Max number of products to return (1-20)

    Returns:
        list[Product]: List of Product objects
    """
    query = db.query(Product)

    return (
        query
        .order_by(Product.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)) -> Product:
    """
    Returns a Product object by product_id

    Args:
        product_id (int): ID of the product to fetch
        db (Session): Current session

    Returns:
        Product: Product object

    Raises:
        HTTPException: 404 if the product doesn't exist
    """
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )
    return product



# --- Order CRUD
@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),) -> Order:
    """
    Creates a "pending" order for current user

    Args:
        payload (OrderCreate): Request body with product_id and quantity
        current_user (User): Logged in user, owner of the new order
        db (Session): Current session

    Returns:
        Order: Created Order object with DB-generated id and created_at

    Raises:
        HTTPException: 400 if the product doesn't exist
    """
    
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(
            status_code=400,
            detail="Product does not exist"
        )

    order = Order(**payload.model_dump(), user_id=current_user.id, status=AllowedStatus.pending)
    db.add(order)
    db.commit()
    db.refresh(order)

    return order


@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0), # ?skip=1
    limit: int = Query(10, ge=1, le=20),
    product_id: int | None = None,
    status: AllowedStatus | None = None) -> list[Order]:
    """
    Returns paginated list of orders ordered by ID, filtered if filters are passed.
    Regular users get only their own orders, admins get all orders

    Args:
        db (Session): Current session
        current_user (User): Logged in user
        skip (int): Number of orders to skip (offset)
        limit (int): Max number of orders to return (1-20)
        product_id (int | None): Filter by product
        status (str | None): Filter by order status

    Returns:
        list[Order]: List of Order objects
    """

    query = db.query(Order)
    if current_user.role != "admin":
        query = query.filter(Order.user_id == current_user.id)
    if not (product_id is None):
        query = query.filter(Order.product_id == product_id)
    if not (status is None):
        query = query.filter(Order.status == status)

    return (
        query
        .order_by(Order.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)) -> Order:
    """
    Returns an Order object by order_id if it belongs to current user (or user is admin)

    Args:
        order_id (int): ID of the order to fetch
        current_user (User): Logged in user
        db (Session): Current session

    Returns:
        Order: Order object

    Raises:
        HTTPException: 404 if the order doesn't exist,
        403 if it belongs to another user and current user is not admin
    """

    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to view this order")

    return order


@app.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(
    payload: OrderUpdate,
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),) -> Order:

    """
    Partially updates an order, only the fields sent in the request body are changed

    Args:
        payload (OrderUpdate): Request body with the fields to change (quantity, status)
        order_id (int): ID of the order to update
        current_user (User): Logged in user
        db (Session): Current session

    Returns:
        Order: Updated Order object

    Raises:
        HTTPException: 404 if the order doesn't exist,
            403 if it belongs to another user and current user is not admin
    """

    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to edit this order")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    db.commit()
    db.refresh(order)
    return order

@app.delete("/orders/{order_id}", status_code=204)
def delete_order(
    order_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)):
    """
    Deletes an order, admin only

    Args:
        order_id (int): ID of the order to delete
        admin (User): Logged in admin (only used for the admin check)
        db (Session): Current session

    Returns:
        Response: Empty 204 (No Content) response

    Raises:
        HTTPException: 404 if the order doesn't exist, 403 if user is not admin
    """

    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()
    return Response(status_code=204)

@app.get("/test")
def test():
    return {"message": "Hello World"}

# 3.2 Orders CRUD (required)
# POST /orders — create an order for the current user; validate product_id exists (400).
# GET /orders — list the current user's orders, with pagination (skip/limit, capped) and filtering (by status, product_id). An admin may list all orders.
# GET /orders/{id} — fetch one order; 404 if missing, 403 if it belongs to another user.
# PATCH /orders/{id} — partial update (e.g. status); same ownership rules.
# DELETE /orders/{id} — admin-only (require_admin), returning 204.
