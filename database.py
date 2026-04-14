"""
DermAI — Database
------------------
All database tables and setup.
Uses SQLite locally, easy to switch to PostgreSQL for production.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# ── Database setup ────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dermai.db")

# Fix for Railway PostgreSQL URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Tables ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
    email         = Column(String, unique=True, nullable=True)
    phone         = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    is_active     = Column(Boolean, default=True)

    skin_profile  = relationship("SkinProfile", back_populates="user", uselist=False)
    orders        = relationship("Order", back_populates="user")
    wishlist      = relationship("WishlistItem", back_populates="user")
    cart          = relationship("CartItem", back_populates="user")
    addresses     = relationship("Address", back_populates="user")


class SkinProfile(Base):
    __tablename__ = "skin_profiles"

    id            = Column(String, primary_key=True)
    user_id       = Column(String, ForeignKey("users.id"), unique=True)
    skin_type     = Column(String, nullable=True)
    concerns      = Column(Text, nullable=True)    # JSON string
    personality   = Column(String, default="friend")
    updated_at    = Column(DateTime, default=datetime.utcnow)

    user          = relationship("User", back_populates="skin_profile")


class Product(Base):
    __tablename__ = "products"

    id            = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
    brand         = Column(String, nullable=False)
    price         = Column(Float, nullable=False)
    category      = Column(String, nullable=False)
    emoji         = Column(String, default="🧴")
    description   = Column(Text, nullable=True)
    targets       = Column(Text, nullable=True)    # JSON string
    skin_types    = Column(Text, nullable=True)    # JSON string
    in_stock      = Column(Boolean, default=True)
    image_url     = Column(String, nullable=True)


class CartItem(Base):
    __tablename__ = "cart_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(String, ForeignKey("users.id"))
    product_id    = Column(String, ForeignKey("products.id"))
    quantity      = Column(Integer, default=1)
    added_at      = Column(DateTime, default=datetime.utcnow)

    user          = relationship("User", back_populates="cart")
    product       = relationship("Product")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(String, ForeignKey("users.id"))
    product_id    = Column(String, ForeignKey("products.id"))
    added_at      = Column(DateTime, default=datetime.utcnow)

    user          = relationship("User", back_populates="wishlist")
    product       = relationship("Product")


class Address(Base):
    __tablename__ = "addresses"

    id            = Column(String, primary_key=True)
    user_id       = Column(String, ForeignKey("users.id"))
    name          = Column(String, nullable=False)
    phone         = Column(String, nullable=False)
    line1         = Column(String, nullable=False)
    line2         = Column(String, nullable=True)
    city          = Column(String, nullable=False)
    state         = Column(String, nullable=False)
    pincode       = Column(String, nullable=False)
    is_default    = Column(Boolean, default=False)

    user          = relationship("User", back_populates="addresses")


class Order(Base):
    __tablename__ = "orders"

    id               = Column(String, primary_key=True)
    user_id          = Column(String, ForeignKey("users.id"))
    total_amount     = Column(Float, nullable=False)
    status           = Column(String, default="placed")
    # Status: placed → confirmed → packed → shipped → out_for_delivery → delivered
    payment_method   = Column(String, default="cod")   # cod | online
    payment_status   = Column(String, default="pending")  # pending | paid | failed
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    address_id       = Column(String, ForeignKey("addresses.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow)

    user             = relationship("User", back_populates="orders")
    items            = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(String, ForeignKey("orders.id"))
    product_id    = Column(String, ForeignKey("products.id"))
    quantity      = Column(Integer, default=1)
    price_at_time = Column(Float, nullable=False)

    order         = relationship("Order", back_populates="items")
    product       = relationship("Product")


# ── DB dependency for FastAPI ─────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Create all tables ─────────────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
    seed_products()
    print("[DermAI] Database initialized.")


# ── Seed product catalog ──────────────────────────────────────────────────────
def seed_products():
    import json
    db = SessionLocal()
    try:
        if db.query(Product).count() > 0:
            return  # Already seeded

        products = [
            Product(id="MIN-NIA-01", name="Niacinamide 10% + Zinc 1%",       brand="Minimalist", price=599,  category="Serum",       emoji="🧴", targets=json.dumps(["dark_spots","open_pores","acne","hyperpigmentation"]), skin_types=json.dumps(["oily","combination"])),
            Product(id="DK-HA-01",   name="Hyaluronic Acid Moisturiser",      brand="Dot & Key",  price=895,  category="Moisturiser", emoji="💧", targets=json.dumps(["dehydration","dullness"]),                            skin_types=json.dumps(["dry","combination","sensitive"])),
            Product(id="PLM-EYE-01", name="Bright Years Under-Eye Gel",       brand="Plum",       price=795,  category="Eye care",    emoji="✨", targets=json.dumps(["dark_circles","fine_lines"]),                         skin_types=json.dumps(["all"])),
            Product(id="MIN-SPF-01", name="SPF 50 Sunscreen PA++++",          brand="Minimalist", price=399,  category="Sunscreen",   emoji="☀️", targets=json.dumps(["hyperpigmentation","dark_spots"]),                    skin_types=json.dumps(["all"])),
            Product(id="PLM-VIT-01", name="15% Vitamin C Face Serum",         brand="Plum",       price=845,  category="Serum",       emoji="🍋", targets=json.dumps(["hyperpigmentation","dullness","dark_spots"]),         skin_types=json.dumps(["all"])),
            Product(id="CVE-MOI-01", name="Moisturising Cream",               brand="CeraVe",     price=1200, category="Moisturiser", emoji="🫙", targets=json.dumps(["dehydration","sensitivity","redness"]),              skin_types=json.dumps(["sensitive","dry"])),
            Product(id="MIN-ARB-01", name="Alpha Arbutin 2% + HA",            brand="Minimalist", price=549,  category="Serum",       emoji="💎", targets=json.dumps(["dark_spots","hyperpigmentation","dullness"]),         skin_types=json.dumps(["all"])),
            Product(id="DK-BHA-01",  name="2% BHA Exfoliating Serum",         brand="Dot & Key",  price=749,  category="Exfoliant",   emoji="🔬", targets=json.dumps(["blackheads","open_pores","uneven_texture","acne"]),  skin_types=json.dumps(["oily","combination"])),
            Product(id="MIN-RET-01", name="Granactive Retinoid 2%",           brand="Minimalist", price=649,  category="Serum",       emoji="⭐", targets=json.dumps(["fine_lines","uneven_texture"]),                       skin_types=json.dumps(["normal","combination"])),
            Product(id="PLM-CLE-01", name="pH Balanced Face Wash",            brand="Plum",       price=299,  category="Cleanser",    emoji="🫧", targets=json.dumps(["all"]),                                              skin_types=json.dumps(["all"])),
        ]
        db.add_all(products)
        db.commit()
        print("[DermAI] Products seeded.")
    finally:
        db.close()
