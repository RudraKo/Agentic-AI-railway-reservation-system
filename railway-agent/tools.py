"""
tools.py - Tool functions callable by the AI agent for database operations.
"""

from datetime import date, timedelta
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Train, Booking
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _sanitize_city(value: str) -> str:
    """Strip whitespace and title-case a city name."""
    return value.strip().title()


def _coerce_travel_date(travel_date: str) -> tuple[str | None, str | None]:
    """
    Coerce travel_date to YYYY-MM-DD and validate it's not in the past.
    Returns (normalized_date, error_message).
    """
    raw = travel_date.strip()
    lowered = raw.lower()

    if lowered == "today":
        normalized = date.today().isoformat()
    elif lowered == "tomorrow":
        normalized = (date.today() + timedelta(days=1)).isoformat()
    else:
        try:
            normalized = date.fromisoformat(raw).isoformat()
        except ValueError:
            return None, "Invalid date format. Please use YYYY-MM-DD."

    try:
        if date.fromisoformat(normalized) < date.today():
            return None, "Travel date cannot be in the past."
    except Exception:
        return None, "Invalid date format."

    return normalized, None


def _generate_ticket_id() -> str:
    """Generate compact ticket IDs like T1A2B3C."""
    return f"T{uuid.uuid4().hex[:6].upper()}"

def search_trains(source: str, destination: str, travel_date: str, db: Session) -> dict:
    """
    Search for trains between source and destination.
    Sanitizes city names and validates travel_date is not in the past.
    """
    source = _sanitize_city(source)
    destination = _sanitize_city(destination)

    travel_date, date_error = _coerce_travel_date(travel_date)
    if date_error:
        return {"success": False, "message": date_error}

    try:
        trains = db.query(Train).filter(
            func.lower(Train.source) == source.lower(),
            func.lower(Train.destination) == destination.lower()
        ).all()

        if not trains:
            return {"trains": [], "message": f"No trains found from {source} to {destination}"}

        return {
            "trains": [
                {
                    "train_no": t.train_no,
                    "name": t.name,
                    "source": t.source,
                    "destination": t.destination,
                    "departure": t.departure,
                    "arrival": t.arrival,
                    "available_seats": t.available_seats,
                    "fare": t.fare
                } for t in trains
            ]
        }
    except Exception as e:
        logger.error(f"Error in search_trains: {str(e)}")
        return {"error": "Internal server error while searching trains"}


def check_availability(train_no: str, travel_date: str, db: Session) -> dict:
    """
    Return seat availability for a specific train and travel date.
    """
    train_no = train_no.strip()
    travel_date, date_error = _coerce_travel_date(travel_date)
    if date_error:
        return {"success": False, "message": date_error}

    try:
        train = db.query(Train).filter(Train.train_no == train_no).first()
        if not train:
            return {"success": False, "message": f"Train {train_no} not found"}

        return {
            "success": True,
            "train_no": train.train_no,
            "train_name": train.name,
            "travel_date": travel_date,
            "available_seats": train.available_seats,
            "total_seats": train.total_seats,
            "fare": train.fare,
            "can_book": train.available_seats > 0,
            "message": (
                f"{train.available_seats} seat(s) available on train {train.train_no} "
                f"for {travel_date}."
            ),
        }
    except Exception as e:
        logger.error(f"Error in check_availability: {str(e)}")
        return {"success": False, "message": "Internal server error while checking availability"}


def process_payment(amount: float, user_id: int | None = None) -> dict:
    """
    Simulate payment processing for a booking.
    """
    if amount <= 0:
        return {"success": False, "payment_status": "FAILED", "message": "Invalid payment amount."}

    payment_ref = f"PAY-{uuid.uuid4().hex[:10].upper()}"
    return {
        "success": True,
        "payment_status": "PAID",
        "payment_reference": payment_ref,
        "user_id": user_id,
        "amount": round(float(amount), 2),
        "message": f"Payment successful. Ref: {payment_ref}",
    }


def book_ticket(
    train_no: str,
    passenger_name: str,
    travel_date: str,
    db: Session,
    user_id: int | None = None,
    payment_status: str = "PENDING",
    payment_reference: str | None = None,
) -> dict:
    """
    Book a ticket for a specific train.
    """
    train_no = train_no.strip()
    passenger_name = passenger_name.strip().title()

    if passenger_name.lower() in ["unknown", "required", "", "none"]:
        return {"success": False, "message": "Passenger name missing."}

    travel_date, date_error = _coerce_travel_date(travel_date)
    if date_error:
        return {"success": False, "message": date_error}

    try:
        train = db.query(Train).filter(Train.train_no == train_no).first()
        if not train:
            return {"success": False, "message": f"Train {train_no} not found"}
        
        if train.available_seats <= 0:
            return {"success": False, "message": "No seats available"}
        
        train.available_seats -= 1
        
        ticket_id = _generate_ticket_id()
        if payment_status == "PENDING":
            payment_status = "PAID"
            payment_reference = f"MOCK-{ticket_id}"

        booking = Booking(
            ticket_id=ticket_id,
            train_no=train_no,
            passenger_name=passenger_name,
            user_id=user_id,
            source=train.source,
            destination=train.destination,
            travel_date=date.fromisoformat(travel_date),
            fare=train.fare,
            status="CONFIRMED",
            payment_reference=payment_reference,
            payment_status=payment_status
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        return {
            "success": True,
            "ticket_id": booking.ticket_id,
            "train_name": train.name,
            "fare": booking.fare,
            "departure": train.departure,
            "arrival": train.arrival,
            "payment_status": booking.payment_status,
            "payment_reference": booking.payment_reference,
            "message": f"Ticket booked successfully for {passenger_name}"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error in book_ticket: {str(e)}")
        return {"success": False, "message": f"Booking failed: {str(e)}"}


def cancel_ticket(ticket_id: str, db: Session, user_id: int | None = None) -> dict:
    """
    Cancel an existing booking by ticket_id.
    """
    ticket_id = ticket_id.strip().upper()

    try:
        query = db.query(Booking).filter(Booking.ticket_id == ticket_id)
        if user_id is not None:
            query = query.filter(Booking.user_id == user_id)
        booking = query.first()
        if not booking:
            return {"success": False, "message": "Ticket not found"}
        
        if booking.status == "CANCELLED":
            return {"success": False, "message": "Ticket already cancelled"}
        
        booking.status = "CANCELLED"
        
        train = db.query(Train).filter(Train.train_no == booking.train_no).first()
        if train:
            train.available_seats += 1
        
        db.commit()
        return {"success": True, "message": f"Ticket {ticket_id} cancelled successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in cancel_ticket: {str(e)}")
        return {"success": False, "message": f"Cancellation failed: {str(e)}"}
