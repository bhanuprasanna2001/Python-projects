"""
Order Microservice
==================
Handles order-related operations.
"""

from fastapi import FastAPI, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from enum import Enum
import httpx


# =============================================================================
# Models
# =============================================================================

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    product_id: str
    name: str
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItem]
    shipping_address: str


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# =============================================================================
# In-Memory Database
# =============================================================================

class OrderDatabase:
    """Simple in-memory order storage."""
    
    def __init__(self):
        self._orders: Dict[int, Dict] = {}
        self._counter = 0
        
        # Add sample orders
        self._add_sample_orders()
    
    def _add_sample_orders(self):
        samples = [
            {
                "user_id": 1,
                "items": [
                    {"product_id": "P001", "name": "Widget", "quantity": 2, "unit_price": 29.99},
                ],
                "shipping_address": "123 Main St",
                "status": "delivered",
            },
            {
                "user_id": 1,
                "items": [
                    {"product_id": "P002", "name": "Gadget", "quantity": 1, "unit_price": 99.99},
                ],
                "shipping_address": "123 Main St",
                "status": "processing",
            },
            {
                "user_id": 2,
                "items": [
                    {"product_id": "P001", "name": "Widget", "quantity": 5, "unit_price": 29.99},
                    {"product_id": "P003", "name": "Accessory", "quantity": 2, "unit_price": 14.99},
                ],
                "shipping_address": "456 Oak Ave",
                "status": "pending",
            },
        ]
        for order in samples:
            self.create(order)
    
    def create(self, data: Dict) -> Dict:
        self._counter += 1
        
        # Calculate total
        total = sum(
            item["quantity"] * item["unit_price"]
            for item in data["items"]
        )
        
        order = {
            "id": self._counter,
            "user_id": data["user_id"],
            "items": data["items"],
            "shipping_address": data["shipping_address"],
            "status": data.get("status", OrderStatus.PENDING.value),
            "total": round(total, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._orders[self._counter] = order
        return order
    
    def get(self, order_id: int) -> Optional[Dict]:
        return self._orders.get(order_id)
    
    def get_all(self) -> List[Dict]:
        return list(self._orders.values())
    
    def get_by_user(self, user_id: int) -> List[Dict]:
        return [
            order for order in self._orders.values()
            if order["user_id"] == user_id
        ]
    
    def update_status(self, order_id: int, new_status: str) -> Optional[Dict]:
        if order_id not in self._orders:
            return None
        
        order = self._orders[order_id]
        order["status"] = new_status
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        return order
    
    def delete(self, order_id: int) -> bool:
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False


db = OrderDatabase()


# =============================================================================
# Service Client (for calling other services)
# =============================================================================

class UserServiceClient:
    """Client for User Service."""
    
    USER_SERVICE_URL = "http://localhost:8001"
    
    async def user_exists(self, user_id: int, correlation_id: str = None) -> bool:
        """Check if user exists."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {}
                if correlation_id:
                    headers["X-Correlation-ID"] = correlation_id
                
                response = await client.get(
                    f"{self.USER_SERVICE_URL}/internal/users/{user_id}/exists",
                    headers=headers,
                )
                
                if response.status_code == 200:
                    return response.json().get("exists", False)
                return False
        except Exception as e:
            print(f"Error checking user: {e}")
            # Fail open or fail closed based on requirements
            return True  # Fail open for demo


user_client = UserServiceClient()


# =============================================================================
# App
# =============================================================================

app = FastAPI(
    title="Order Service",
    description="Order management microservice",
    version="1.0.0",
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "service": "Order Service",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "order"}


@app.get("/orders")
async def list_orders(
    user_id: Optional[int] = None,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """List orders, optionally filtered by user."""
    print(f"[{x_correlation_id}] Listing orders (user_id={user_id})")
    
    if user_id:
        return db.get_by_user(user_id)
    return db.get_all()


@app.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Get order by ID."""
    print(f"[{x_correlation_id}] Getting order {order_id}")
    
    order = db.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    return order


@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Create a new order."""
    print(f"[{x_correlation_id}] Creating order for user {data.user_id}")
    
    # Validate user exists (cross-service call)
    user_exists = await user_client.user_exists(
        data.user_id,
        x_correlation_id
    )
    
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {data.user_id} not found"
        )
    
    # Validate items
    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must have at least one item"
        )
    
    order_data = {
        "user_id": data.user_id,
        "items": [item.model_dump() for item in data.items],
        "shipping_address": data.shipping_address,
    }
    
    order = db.create(order_data)
    return order


@app.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Update order status."""
    print(f"[{x_correlation_id}] Updating order {order_id} status to {data.status}")
    
    order = db.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    # Validate status transition
    current_status = order["status"]
    new_status = data.status.value
    
    valid_transitions = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["processing", "cancelled"],
        "processing": ["shipped", "cancelled"],
        "shipped": ["delivered"],
        "delivered": [],
        "cancelled": [],
    }
    
    if new_status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_status} to {new_status}"
        )
    
    updated = db.update_status(order_id, new_status)
    return updated


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Cancel an order."""
    print(f"[{x_correlation_id}] Cancelling order {order_id}")
    
    order = db.get(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    if order["status"] not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending or confirmed orders"
        )
    
    db.update_status(order_id, "cancelled")


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    Order Service
    ================================================
    
    Endpoints:
    - GET /orders - List orders
    - GET /orders?user_id={id} - List orders by user
    - GET /orders/{id} - Get order by ID
    - POST /orders - Create order
    - PATCH /orders/{id}/status - Update order status
    - DELETE /orders/{id} - Cancel order
    
    Order Status Flow:
    pending -> confirmed -> processing -> shipped -> delivered
              \-> cancelled <-/
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
