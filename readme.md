# Orders API

REST API over the course PostgreSQL database (users, orders, products) with FastAPI, SQLAlchemy and JWT authentication.

## Files

- `app/main.py` - FastAPI app and endpoints
- `app/database.py` - engine, SessionLocal and get_db
- `app/models.py` - SQLAlchemy models
- `app/schemas.py` - Pydantic models
- `app/auth.py` - password hashing and JWT
- `app/extensions.py` - enums (AllowedRole, AllowedStatus)
- `demo.py` - demo script

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/<db_name>
SECRET_KEY=<random string>
```

Database needs to be running with `schema.sql` and `seed.sql` loaded.

## Run

```bash
fastapi dev app/main.py
```

Docs: `http://127.0.0.1:8000/docs` (click Authorize and log in, e.g. `user1@example.com` / `password123`)

## Demo

With the server running:

```bash
python demo.py
```

Registers Ada, logs in, creates an order and prints Ada's orders and the new order.

## Endpoints

### Auth

| Method | Path | Description | Raises |
|---|---|---|---|
| POST | `/register` | Registers a new user an adds them into the database | 409 if email has already been registered |
| POST | `/token` | Checks if the email and password match and generates an access token | 401 if the email doesn't exist or the password is incorrect |
| GET | `/me` | Returns an User object with current_user's information | 401 if token is invalid or expired, or if user doesn't exist |

### Orders

| Method | Path | Description | Raises |
|---|---|---|---|
| POST | `/orders` | Creates a "pending" order for current user | 400 if the product doesn't exist |
| GET | `/orders` | Returns paginated list of orders ordered by ID, filtered if filters are passed. Regular users get only their own orders, admins get all orders | |
| GET | `/orders/{order_id}` | Returns an Order object by order_id if it belongs to current user (or user is admin) | 404 if the order doesn't exist, 403 if it belongs to another user and current user is not admin |
| PATCH | `/orders/{order_id}` | Partially updates an order, only the fields sent in the request body are changed | 404 if the order doesn't exist, 403 if it belongs to another user and current user is not admin |
| DELETE | `/orders/{order_id}` | Deletes an order, admin only | 404 if the order doesn't exist, 403 if user is not admin |

`GET /orders` query params: `skip`, `limit` (1-20), `product_id`, `status`

### Products

| Method | Path | Description | Raises |
|---|---|---|---|
| GET | `/products` | Returns paginated list of products ordered by ID | |
| GET | `/products/{product_id}` | Returns a Product object by product_id | 404 if the product doesn't exist |

All endpoints except `/register` and `/token` need `Authorization: Bearer <token>`.

## Notes

- bcrypt is pinned to 4.0.1, newer versions don't work with passlib 1.7.4
