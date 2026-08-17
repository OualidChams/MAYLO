"""
Database models — Postgres via SQLAlchemy 2.0.

Every table is tied to restaurant_id (tenant_id) from day one, because
we're building a multi-restaurant SaaS, not a single-restaurant app
(see architecture decision #7).
"""
import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Organization(Base):
    """
    Tenant boundary ABOVE Restaurant (Platform → Organization → Restaurant).
    Added now — cheap on an empty dev database, expensive to retrofit once
    real orders/calls/users exist. The full RBAC/permissions/audit engine
    that would use this hierarchy is deliberately NOT built yet — see
    ROADMAP.md "Authorization & Multi-tenancy". A single restaurant owner
    is just an Organization with one Restaurant; a chain is one Organization
    with several — same shape, no special-casing later.
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    restaurants: Mapped[list["Restaurant"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = _uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The number the customer dials (E.164) — used to look up the restaurant in the Twilio webhook
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    language: Mapped[str] = mapped_column(String(8), default="en")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="restaurants")
    locations: Mapped[list["Location"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    opening_hours: Mapped[list["OpeningHours"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    calls: Mapped[list["Call"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="locations")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="menu_items")


class OpeningHours(Base):
    __tablename__ = "opening_hours"

    id: Mapped[uuid.UUID] = _uuid_pk()
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    # 0 = Monday ... 6 = Sunday (ISO weekday - 1)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="opening_hours")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = _uuid_pk()
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    twilio_call_sid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    from_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # queued | ringing | in-progress | completed | failed | no-answer ...
    status: Mapped[str] = mapped_column(String(32), default="ringing")
    # outcome filled in later (Days 9-10): order_created | transferred_to_human | no_action ...
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)

    restaurant: Mapped["Restaurant"] = relationship(back_populates="calls")
    orders: Mapped[list["Order"]] = relationship(back_populates="call")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    restaurant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calls.id"), nullable=True, index=True)
    # pending | confirmed | cancelled
    status: Mapped[str] = mapped_column(String(32), default="pending")
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    restaurant: Mapped["Restaurant"] = relationship(back_populates="orders")
    call: Mapped["Call | None"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    # Price at order time — we don't rely on the current menu_items price later
    # (decision #21: never trust the LLM with business truth — same logic applies to prices that can change)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
