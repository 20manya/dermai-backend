"""
DermAI — Orders
----------------
Cart, wishlist, orders, addresses.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import SessionLocal, User, Product, CartItem, WishlistItem, Order, OrderItem, Address
from auth import verify_token

router = APIRouter(tags=["orders"])

RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

def get_razorpay():
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        except Exception:
            return None
    return None

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
    payment_method: str = "cod"

class VerifyPaymentRequest(BaseModel):
    order_id:            str
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str

def get_user_from_token(token: str):
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(401, "Invalid token")
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        raise HTTPException(404, "User not found")
    return user_id

def fmt(p, quantity=None):
    r = {"id": p.id, "name": p.name, "brand": p.brand, "price": p.price, "category": p.category, "emoji": p.emoji, "in_stock": p.in_stock}
    if quantity is not None:
        r["quantity"] = quantity
    return r

@router.get("/cart")
def get_cart(token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
        cart_items = [fmt(item.product, item.quantity) for item in items]
        total = sum(i["price"] * i["quantity"] for i in cart_items)
        return {"items": cart_items, "total": total, "count": len(cart_items)}
    finally:
        db.close()

@router.post("/cart/add")
def add_to_cart(req: AddToCartRequest, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == req.product_id).first()
        if not product:
            raise HTTPException(404, "Product not found")
        if not product.in_stock:
            raise HTTPException(400, "Out of stock")
        existing = db.query(CartItem).filter(CartItem.user_id == user_id, CartItem.product_id == req.product_id).first()
        if existing:
            existing.quantity += req.quantity
        else:
            db.add(CartItem(user_id=user_id, product_id=req.product_id, quantity=req.quantity))
        db.commit()
        return {"message": f"{product.name} added to cart"}
    finally:
        db.close()

@router.put("/cart/{product_id}")
def update_cart(product_id: str, req: UpdateCartRequest, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        item = db.query(CartItem).filter(CartItem.user_id == user_id, CartItem.product_id == product_id).first()
        if not item:
            raise HTTPException(404, "Item not in cart")
        if req.quantity <= 0:
            db.delete(item)
        else:
            item.quantity = req.quantity
        db.commit()
        return {"message": "Cart updated"}
    finally:
        db.close()

@router.delete("/cart/{product_id}")
def remove_from_cart(product_id: str, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        item = db.query(CartItem).filter(CartItem.user_id == user_id, CartItem.product_id == product_id).first()
        if item:
            db.delete(item)
            db.commit()
        return {"message": "Removed from cart"}
    finally:
        db.close()

@router.delete("/cart")
def clear_cart(token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        db.query(CartItem).filter(CartItem.user_id == user_id).delete()
        db.commit()
        return {"message": "Cart cleared"}
    finally:
        db.close()

@router.get("/wishlist")
def get_wishlist(token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        items = db.query(WishlistItem).filter(WishlistItem.user_id == user_id).all()
        return {"items": [fmt(i.product) for i in items]}
    finally:
        db.close()

@router.post("/wishlist/{product_id}")
def toggle_wishlist(product_id: str, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(404, "Product not found")
        existing = db.query(WishlistItem).filter(WishlistItem.user_id == user_id, WishlistItem.product_id == product_id).first()
        if existing:
            db.delete(existing)
            db.commit()
            return {"message": "Removed from wishlist", "wishlisted": False}
        else:
            db.add(WishlistItem(user_id=user_id, product_id=product_id))
            db.commit()
            return {"message": "Added to wishlist", "wishlisted": True}
    finally:
        db.close()

@router.get("/addresses")
def get_addresses(token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        addresses = db.query(Address).filter(Address.user_id == user_id).all()
        return {"addresses": [{"id": a.id, "name": a.name, "phone": a.phone, "line1": a.line1, "line2": a.line2, "city": a.city, "state": a.state, "pincode": a.pincode, "is_default": a.is_default} for a in addresses]}
    finally:
        db.close()

@router.post("/addresses")
def add_address(req: AddAddressRequest, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        if req.is_default:
            db.query(Address).filter(Address.user_id == user_id).update({"is_default": False})
        address = Address(id=str(uuid.uuid4()), user_id=user_id, name=req.name, phone=req.phone, line1=req.line1, line2=req.line2, city=req.city, state=req.state, pincode=req.pincode, is_default=req.is_default)
        db.add(address)
        db.commit()
        return {"message": "Address saved", "address_id": address.id}
    finally:
        db.close()

@router.post("/orders/place")
def place_order(req: PlaceOrderRequest, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        cart_items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
        if not cart_items:
            raise HTTPException(400, "Cart is empty")
        address = db.query(Address).filter(Address.id == req.address_id, Address.user_id == user_id).first()
        if not address:
            raise HTTPException(404, "Address not found")
        total    = sum(item.product.price * item.quantity for item in cart_items)
        order_id = f"DMA-{str(uuid.uuid4())[:8].upper()}"
        order    = Order(id=order_id, user_id=user_id, total_amount=total, payment_method=req.payment_method, payment_status="paid" if req.payment_method == "cod" else "pending", address_id=req.address_id)
        db.add(order)
        for ci in cart_items:
            db.add(OrderItem(order_id=order_id, product_id=ci.product_id, quantity=ci.quantity, price_at_time=ci.product.price))
        razorpay_data = None
        if req.payment_method == "online":
            rp = get_razorpay()
            if rp:
                try:
                    rp_order = rp.order.create({"amount": int(total * 100), "currency": "INR", "receipt": order_id})
                    order.razorpay_order_id = rp_order["id"]
                    razorpay_data = {"razorpay_order_id": rp_order["id"], "amount": int(total * 100), "currency": "INR", "key_id": RAZORPAY_KEY_ID}
                except Exception:
                    pass
        db.query(CartItem).filter(CartItem.user_id == user_id).delete()
        db.commit()
        return {"message": "Order placed!", "order_id": order_id, "total": total, "payment_method": req.payment_method, "razorpay": razorpay_data}
    finally:
        db.close()

@router.get("/orders")
def get_orders(token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()
        STATUS_STEPS = ["placed", "confirmed", "packed", "shipped", "out_for_delivery", "delivered"]
        return {"orders": [{"id": o.id, "total": o.total_amount, "status": o.status, "status_step": STATUS_STEPS.index(o.status) if o.status in STATUS_STEPS else 0, "total_steps": len(STATUS_STEPS), "payment_method": o.payment_method, "payment_status": o.payment_status, "created_at": o.created_at.isoformat(), "items": [{"name": i.product.name, "brand": i.product.brand, "emoji": i.product.emoji, "quantity": i.quantity, "price": i.price_at_time} for i in o.items]} for o in orders]}
    finally:
        db.close()

@router.get("/orders/{order_id}")
def get_order(order_id: str, token: str):
    user_id = get_user_from_token(token)
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        if not order:
            raise HTTPException(404, "Order not found")
        STATUS_STEPS = ["placed", "confirmed", "packed", "shipped", "out_for_delivery", "delivered"]
        return {"id": order.id, "total": order.total_amount, "status": order.status, "status_step": STATUS_STEPS.index(order.status) if order.status in STATUS_STEPS else 0, "total_steps": len(STATUS_STEPS), "payment_method": order.payment_method, "payment_status": order.payment_status, "created_at": order.created_at.isoformat(), "items": [{"name": i.product.name, "brand": i.product.brand, "emoji": i.product.emoji, "quantity": i.quantity, "price": i.price_at_time} for i in order.items]}
    finally:
        db.close()