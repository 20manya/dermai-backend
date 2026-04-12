"""
DermAI — Orders
----------------
Handles:
  - Cart (add, remove, update quantity)
  - Wishlist (save products for later)
  - Orders (place, track, history)
  - Payments (Razorpay + COD)
  - Addresses (save delivery addresses)
"""

import os
import uuid
import json
from datetime import datetime
from typing import Optional

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, User, Product, CartItem, WishlistItem, Order, OrderItem, Address
from auth import get_current_user, verify_token

router = APIRouter(tags=["orders"])

# ── Razorpay client ───────────────────────────────────────────────────────────
RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

def get_razorpay():
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    return None

# ── Request models ────────────────────────────────────────────────────────────
class AddToCartRequest(BaseModel):
    product_id: str
    quantity:   int = 1

class UpdateCartRequest(BaseModel):
    quantity: int

class AddAddressRequest(BaseModel):
    name:       str
    phone:      str
    line1:      str
    line2:      Optional[str] = None
    city:       str
    state:      str
    pincode:    str
    is_default: bool = False

class PlaceOrderRequest(BaseModel):
    address_id:     str
    payment_method: str = "cod"   # cod | online

class VerifyPaymentRequest(BaseModel):
    order_id:           str
    razorpay_order_id:  str
    razorpay_payment_id: str
    razorpay_signature: str

# ── Helper: get user from token ───────────────────────────────────────────────
def get_user(token: str, db: Session) -> User:
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user

def format_product(p: Product, quantity: int = None) -> dict:
    result = {
        "id":       p.id,
        "name":     p.name,
        "brand":    p.brand,
        "price":    p.price,
        "category": p.category,
        "emoji":    p.emoji,
        "in_stock": p.in_stock,
    }
    if quantity is not None:
        result["quantity"] = quantity
    return result

# ══════════════════════════════════════════════════════
# CART
# ══════════════════════════════════════════════════════

@router.get("/cart")
def get_cart(token: str, db: Session = Depends(get_db)):
    user  = get_user(token, db)
    items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    cart_items = [format_product(item.product, item.quantity) for item in items]
    total = sum(i["price"] * i["quantity"] for i in cart_items)
    return {"items": cart_items, "total": total, "count": len(cart_items)}


@router.post("/cart/add")
def add_to_cart(req: AddToCartRequest, token: str, db: Session = Depends(get_db)):
    user    = get_user(token, db)
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    if not product.in_stock:
        raise HTTPException(400, "Product is out of stock")

    existing = db.query(CartItem).filter(
        CartItem.user_id == user.id,
        CartItem.product_id == req.product_id
    ).first()

    if existing:
        existing.quantity += req.quantity
    else:
        db.add(CartItem(user_id=user.id, product_id=req.product_id, quantity=req.quantity))

    db.commit()
    return {"message": f"{product.name} added to cart"}


@router.put("/cart/{product_id}")
def update_cart(product_id: str, req: UpdateCartRequest, token: str, db: Session = Depends(get_db)):
    user = get_user(token, db)
    item = db.query(CartItem).filter(
        CartItem.user_id == user.id,
        CartItem.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(404, "Item not in cart")

    if req.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = req.quantity
    db.commit()
    return {"message": "Cart updated"}


@router.delete("/cart/{product_id}")
def remove_from_cart(product_id: str, token: str, db: Session = Depends(get_db)):
    user = get_user(token, db)
    item = db.query(CartItem).filter(
        CartItem.user_id == user.id,
        CartItem.product_id == product_id
    ).first()
    if item:
        db.delete(item)
        db.commit()
    return {"message": "Removed from cart"}


@router.delete("/cart")
def clear_cart(token: str, db: Session = Depends(get_db)):
    user = get_user(token, db)
    db.query(CartItem).filter(CartItem.user_id == user.id).delete()
    db.commit()
    return {"message": "Cart cleared"}


# ══════════════════════════════════════════════════════
# WISHLIST
# ══════════════════════════════════════════════════════

@router.get("/wishlist")
def get_wishlist(token: str, db: Session = Depends(get_db)):
    user  = get_user(token, db)
    items = db.query(WishlistItem).filter(WishlistItem.user_id == user.id).all()
    return {"items": [format_product(i.product) for i in items]}


@router.post("/wishlist/{product_id}")
def toggle_wishlist(product_id: str, token: str, db: Session = Depends(get_db)):
    user    = get_user(token, db)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")

    existing = db.query(WishlistItem).filter(
        WishlistItem.user_id == user.id,
        WishlistItem.product_id == product_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Removed from wishlist", "wishlisted": False}
    else:
        db.add(WishlistItem(user_id=user.id, product_id=product_id))
        db.commit()
        return {"message": "Added to wishlist", "wishlisted": True}


# ══════════════════════════════════════════════════════
# ADDRESSES
# ══════════════════════════════════════════════════════

@router.get("/addresses")
def get_addresses(token: str, db: Session = Depends(get_db)):
    user = get_user(token, db)
    addresses = db.query(Address).filter(Address.user_id == user.id).all()
    return {"addresses": [
        {
            "id":         a.id,
            "name":       a.name,
            "phone":      a.phone,
            "line1":      a.line1,
            "line2":      a.line2,
            "city":       a.city,
            "state":      a.state,
            "pincode":    a.pincode,
            "is_default": a.is_default
        } for a in addresses
    ]}


@router.post("/addresses")
def add_address(req: AddAddressRequest, token: str, db: Session = Depends(get_db)):
    user = get_user(token, db)

    if req.is_default:
        # Remove default from other addresses
        db.query(Address).filter(Address.user_id == user.id).update({"is_default": False})

    address = Address(
        id         = str(uuid.uuid4()),
        user_id    = user.id,
        name       = req.name,
        phone      = req.phone,
        line1      = req.line1,
        line2      = req.line2,
        city       = req.city,
        state      = req.state,
        pincode    = req.pincode,
        is_default = req.is_default
    )
    db.add(address)
    db.commit()
    return {"message": "Address saved", "address_id": address.id}


# ══════════════════════════════════════════════════════
# ORDERS
# ══════════════════════════════════════════════════════

@router.post("/orders/place")
def place_order(req: PlaceOrderRequest, token: str, db: Session = Depends(get_db)):
    user = get_user(token, db)

    # Get cart
    cart_items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    if not cart_items:
        raise HTTPException(400, "Cart is empty")

    # Verify address
    address = db.query(Address).filter(
        Address.id == req.address_id,
        Address.user_id == user.id
    ).first()
    if not address:
        raise HTTPException(404, "Address not found")

    # Calculate total
    total = sum(item.product.price * item.quantity for item in cart_items)

    # Create order
    order_id = f"DMA-{str(uuid.uuid4())[:8].upper()}"
    order    = Order(
        id             = order_id,
        user_id        = user.id,
        total_amount   = total,
        payment_method = req.payment_method,
        payment_status = "paid" if req.payment_method == "cod" else "pending",
        address_id     = req.address_id
    )
    db.add(order)

    # Add order items
    for cart_item in cart_items:
        db.add(OrderItem(
            order_id      = order_id,
            product_id    = cart_item.product_id,
            quantity      = cart_item.quantity,
            price_at_time = cart_item.product.price
        ))

    # If online payment — create Razorpay order
    razorpay_data = None
    if req.payment_method == "online":
        rp = get_razorpay()
        if rp:
            rp_order = rp.order.create({
                "amount":   int(total * 100),   # In paise
                "currency": "INR",
                "receipt":  order_id,
            })
            order.razorpay_order_id = rp_order["id"]
            razorpay_data = {
                "razorpay_order_id": rp_order["id"],
                "amount":            int(total * 100),
                "currency":          "INR",
                "key_id":            RAZORPAY_KEY_ID
            }

    # Clear cart
    db.query(CartItem).filter(CartItem.user_id == user.id).delete()
    db.commit()

    return {
        "message":      "Order placed successfully!",
        "order_id":     order_id,
        "total":        total,
        "payment_method": req.payment_method,
        "razorpay":     razorpay_data
    }


@router.post("/orders/verify-payment")
def verify_payment(req: VerifyPaymentRequest, token: str, db: Session = Depends(get_db)):
    """Verify Razorpay payment signature"""
    user  = get_user(token, db)
    order = db.query(Order).filter(Order.id == req.order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    rp = get_razorpay()
    if rp:
        try:
            rp.utility.verify_payment_signature({
                "razorpay_order_id":   req.razorpay_order_id,
                "razorpay_payment_id": req.razorpay_payment_id,
                "razorpay_signature":  req.razorpay_signature
            })
            order.payment_status    = "paid"
            order.razorpay_payment_id = req.razorpay_payment_id
            order.status            = "confirmed"
            db.commit()
            return {"message": "Payment verified!", "order_id": order.id}
        except:
            raise HTTPException(400, "Payment verification failed")

    return {"message": "Payment recorded"}


@router.get("/orders")
def get_orders(token: str, db: Session = Depends(get_db)):
    """Get all orders for user"""
    user   = get_user(token, db)
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()

    STATUS_STEPS = ["placed", "confirmed", "packed", "shipped", "out_for_delivery", "delivered"]

    return {"orders": [
        {
            "id":             o.id,
            "total":          o.total_amount,
            "status":         o.status,
            "status_step":    STATUS_STEPS.index(o.status) if o.status in STATUS_STEPS else 0,
            "total_steps":    len(STATUS_STEPS),
            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "created_at":     o.created_at.isoformat(),
            "items": [
                {
                    "product_id":   item.product_id,
                    "name":         item.product.name,
                    "brand":        item.product.brand,
                    "emoji":        item.product.emoji,
                    "quantity":     item.quantity,
                    "price":        item.price_at_time
                } for item in o.items
            ]
        } for o in orders
    ]}


@router.get("/orders/{order_id}")
def get_order(order_id: str, token: str, db: Session = Depends(get_db)):
    """Get single order details"""
    user  = get_user(token, db)
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    STATUS_STEPS = ["placed", "confirmed", "packed", "shipped", "out_for_delivery", "delivered"]

    return {
        "id":             order.id,
        "total":          order.total_amount,
        "status":         order.status,
        "status_step":    STATUS_STEPS.index(order.status) if order.status in STATUS_STEPS else 0,
        "total_steps":    len(STATUS_STEPS),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "created_at":     order.created_at.isoformat(),
        "items": [
            {
                "name":     item.product.name,
                "brand":    item.product.brand,
                "emoji":    item.product.emoji,
                "quantity": item.quantity,
                "price":    item.price_at_time
            } for item in order.items
        ]
    }
