"""
Products Microservice
=====================
Handles product-related operations.
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import sys
sys.path.insert(0, '..')

from shared.models import ProductCreate, ProductUpdate, ProductResponse, ProductCategory
from shared.dependencies import pagination_params

app = FastAPI(title="Products Service", version="1.0.0")

# In-memory database for demo
products_db: dict = {
    1: {
        "id": 1,
        "name": "Laptop",
        "description": "High-performance laptop",
        "price": 999.99,
        "category": ProductCategory.ELECTRONICS,
        "stock": 50,
        "is_active": True,
        "created_at": datetime.utcnow()
    },
    2: {
        "id": 2,
        "name": "Python Book",
        "description": "Learn Python programming",
        "price": 29.99,
        "category": ProductCategory.BOOKS,
        "stock": 100,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
}
next_id = 3


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "products"}


@app.get("/stats")
async def stats():
    return {
        "total_products": len(products_db),
        "total_stock": sum(p["stock"] for p in products_db.values()),
        "categories": list(set(str(p["category"]) for p in products_db.values()))
    }


@app.get("/", response_model=List[ProductResponse])
async def list_products(
    pagination: dict = Depends(pagination_params),
    category: Optional[ProductCategory] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0)
):
    """List all products with filtering."""
    products = list(products_db.values())
    
    if category:
        products = [p for p in products if p["category"] == category]
    
    if min_price is not None:
        products = [p for p in products if p["price"] >= min_price]
    
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    
    start = pagination["skip"]
    end = start + pagination["per_page"]
    
    return products[start:end]


@app.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """Get product by ID."""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    return products_db[product_id]


@app.post("/", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    """Create a new product."""
    global next_id
    
    new_product = {
        "id": next_id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "category": product.category,
        "stock": product.stock,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    products_db[next_id] = new_product
    next_id += 1
    
    return new_product


@app.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_update: ProductUpdate):
    """Update product fields."""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = products_db[product_id]
    update_data = product_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        product[key] = value
    
    return product


@app.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int):
    """Delete a product."""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    del products_db[product_id]


@app.post("/{product_id}/stock")
async def update_stock(product_id: int, quantity: int = Query(...)):
    """Update product stock (add or subtract)."""
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = products_db[product_id]
    new_stock = product["stock"] + quantity
    
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    product["stock"] = new_stock
    return {"product_id": product_id, "new_stock": new_stock}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
