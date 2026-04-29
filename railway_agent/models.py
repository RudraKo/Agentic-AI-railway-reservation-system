"""
models.py - SQLAlchemy models for the Railway Reservation System.
"""
import uuid
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Date
from sqlalchemy.sql import func
from database import Base


def _generate_ticket_id() -> str:
    """Generate compact ticket IDs like T1A2B3C."""
    return f"T{uuid.uuid4().hex[:6].upper()}"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class Train(Base):
    __tablename__ = "trains"

    id = Column(Integer, primary_key=True, index=True)
    train_no = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure = Column(String, nullable=False)  # Stored as HH:MM
    arrival = Column(String, nullable=False)    # Stored as HH:MM
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    fare = Column(Float, nullable=False)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, unique=True, index=True, nullable=False, default=_generate_ticket_id)
    train_no = Column(String, ForeignKey("trains.train_no"), nullable=False)
    passenger_name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    travel_date = Column(Date, nullable=False)
    fare = Column(Float, nullable=False)
    status = Column(String, default="CONFIRMED")  # CONFIRMED, CANCELLED
    payment_status = Column(String, default="PENDING")  # PENDING, PAID, FAILED
    payment_reference = Column(String, nullable=True)
    booking_time = Column(DateTime(timezone=True), server_default=func.now())
    # Relationship
    # user = relationship("User", back_populates="bookings")