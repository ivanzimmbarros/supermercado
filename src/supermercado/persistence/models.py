from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeoContext(Base):
    __tablename__ = "geo_contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    postal_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    locality: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="frozen")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)

    snapshots: Mapped[list[PriceSnapshot]] = relationship(back_populates="geo_context")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))


class SettingsAudit(Base):
    __tablename__ = "settings_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    changed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="PT")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)


class MarketPreference(Base):
    __tablename__ = "market_preferences"
    __table_args__ = (UniqueConstraint("market_id", "geo_context_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    market_id: Mapped[str] = mapped_column(String(40), ForeignKey("markets.id"), nullable=False)
    geo_context_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geo_contexts.id"), nullable=False
    )
    preferred_store_id: Mapped[str | None] = mapped_column(String(80))
    preferred_store_name: Mapped[str | None] = mapped_column(String(200))
    extra_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(120))
    quantity_value: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(16))
    pack_count: Mapped[int] = mapped_column(Integer, default=1)
    ean: Mapped[str | None] = mapped_column(String(32), index=True)
    attributes_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketProduct(Base):
    __tablename__ = "market_products"
    __table_args__ = (UniqueConstraint("market_id", "external_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    market_id: Mapped[str] = mapped_column(String(40), ForeignKey("markets.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120))
    ean: Mapped[str | None] = mapped_column(String(32), index=True)
    quantity_value: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(16))
    pack_count: Mapped[int] = mapped_column(Integer, default=1)
    url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductMatch(Base):
    __tablename__ = "product_matches"
    __table_args__ = (UniqueConstraint("product_id", "market_product_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    market_product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("market_products.id"), nullable=False
    )
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    unit_factor: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geo_context_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geo_contexts.id"), nullable=False, index=True
    )
    market_product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("market_products.id"), nullable=False
    )
    product_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("products.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price_final: Mapped[float] = mapped_column(Float, nullable=False)
    price_before: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_promo: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_label: Mapped[str | None] = mapped_column(String(200))
    promo_valid_until: Mapped[date | None] = mapped_column(Date)
    unit_price_final: Mapped[float] = mapped_column(Float, nullable=False)
    unit_basis: Mapped[str] = mapped_column(String(8), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    availability_label: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(40), default="live_query")

    geo_context: Mapped[GeoContext] = relationship(back_populates="snapshots")


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="ativa")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ListItem(Base):
    __tablename__ = "list_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    list_id: Mapped[str] = mapped_column(String(36), ForeignKey("shopping_lists.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False)
    quantity_desired: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text)
    selected_market_product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("market_products.id")
    )
    status: Mapped[str] = mapped_column(String(20), default="pendente")


class RecurringProduct(Base):
    __tablename__ = "recurring_products"

    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cadence_key: Mapped[str] = mapped_column(String(40), default="configured_schedule")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_name: Mapped[str] = mapped_column(String(80), nullable=False)
    geo_context_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("geo_contexts.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
