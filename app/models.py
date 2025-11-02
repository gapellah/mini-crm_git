"""ミニCRMで扱うデータモデルと共通カラム定義をまとめたモジュール。"""

from datetime import date

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

class TimestampMixin:
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="member", nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"


class Property(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    note = db.Column(db.Text, nullable=True)

    leases = db.relationship("Lease", back_populates="property", cascade="all, delete-orphan")
    tenants = db.relationship("Tenant", back_populates="property", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Property {self.name}>"


class Tenant(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=True)
    unit_number = db.Column(db.String(50), nullable=True)

    leases = db.relationship("Lease", back_populates="tenant", cascade="all, delete-orphan")
    property = db.relationship("Property", back_populates="tenants")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tenant {self.name}>"


class LeaseStatus:
    ACTIVE = "active"
    PENDING = "pending"
    TERMINATED = "terminated"

    ALL = (ACTIVE, PENDING, TERMINATED)


class Lease(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    rent = db.Column(db.Numeric(10, 2), nullable=False)
    unit_number = db.Column(db.String(50), nullable=True)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), nullable=False, default=LeaseStatus.PENDING)

    property = db.relationship("Property", back_populates="leases")
    tenant = db.relationship("Tenant", back_populates="leases")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lease {self.id}: {self.property_id} -> {self.tenant_id}>"
