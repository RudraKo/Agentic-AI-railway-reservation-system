"""
routes/tickets.py - REST endpoints for direct ticket and train operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from database import get_db
from models import Train, Booking, User

router = APIRouter()


# ---------------------------------------------------------------------------
# Ticket endpoints
# ---------------------------------------------------------------------------

@router.get("/tickets")
def get_confirmed_tickets(
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """GET /api/tickets — Return confirmed bookings, optionally scoped by user."""
    rows = (
        db.query(Booking, Train)
        .outerjoin(Train, Booking.train_no == Train.train_no)
    )
    if user_id is not None:
        rows = rows.filter(Booking.user_id == user_id)
    elif user_name:
        rows = rows.filter(func.lower(Booking.passenger_name) == user_name.lower())

    rows = rows.order_by(Booking.booking_time.desc()).all()

    tickets = []
    for booking, train in rows:
        tickets.append(
            {
                "ticket_id": booking.ticket_id,
                "train_no": booking.train_no,
                "train_name": train.name if train else None,
                "departure": train.departure if train else None,
                "arrival": train.arrival if train else None,
                "passenger_name": booking.passenger_name,
                "source": booking.source,
                "destination": booking.destination,
                "travel_date": booking.travel_date,
                "fare": booking.fare,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "payment_reference": booking.payment_reference,
                "booked_at": booking.booking_time,
            }
        )

    return {"tickets": tickets}


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """GET /api/tickets/{ticket_id} — Return a single booking by ticket ID."""
    booking = db.query(Booking).filter(Booking.ticket_id == ticket_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found")
    train = db.query(Train).filter(Train.train_no == booking.train_no).first()
    return {
        "ticket_id": booking.ticket_id,
        "train_no": booking.train_no,
        "train_name": train.name if train else None,
        "departure": train.departure if train else None,
        "arrival": train.arrival if train else None,
        "passenger_name": booking.passenger_name,
        "source": booking.source,
        "destination": booking.destination,
        "travel_date": booking.travel_date,
        "fare": booking.fare,
        "status": booking.status,
        "payment_status": booking.payment_status,
        "payment_reference": booking.payment_reference,
        "booked_at": booking.booking_time,
    }


@router.post("/tickets/{ticket_id}/pay")
def pay_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """POST /api/tickets/{ticket_id}/pay — Mock payment processor."""
    import uuid
    booking = db.query(Booking).filter(Booking.ticket_id == ticket_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if booking.payment_status == "PAID":
        return {"success": False, "message": "Ticket is already paid."}
        
    booking.payment_status = "PAID"
    booking.payment_reference = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    db.commit()
    
    return {"success": True, "message": "Payment successful", "reference": booking.payment_reference}


# ---------------------------------------------------------------------------
# Train endpoints
# ---------------------------------------------------------------------------

@router.get("/trains")
def get_all_trains(db: Session = Depends(get_db)):
    """GET /api/trains — Return all trains in the database."""
    trains = db.query(Train).all()
    return [
        {
            "train_no": t.train_no,
            "name": t.name,
            "source": t.source,
            "destination": t.destination,
            "departure": t.departure,
            "arrival": t.arrival,
            "total_seats": t.total_seats,
            "available_seats": t.available_seats,
            "fare": t.fare,
        }
        for t in trains
    ]


@router.get("/trains/search")
def search_trains(
    source: Optional[str] = None,
    destination: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    GET /api/trains/search?source=Chennai&destination=Bangalore

    Filter trains by source and destination (case-insensitive).
    Only returns trains with available_seats > 0.
    """
    query = db.query(Train).filter(Train.available_seats > 0)

    if source:
        query = query.filter(func.lower(Train.source) == source.lower())
    if destination:
        query = query.filter(func.lower(Train.destination) == destination.lower())

    trains = query.all()

    if not trains:
        return {"trains": [], "message": "No available trains found for this route"}

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
                "fare": t.fare,
            }
            for t in trains
        ]
    }
