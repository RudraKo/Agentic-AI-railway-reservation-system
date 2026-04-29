"""
main.py - FastAPI application entry point for Agentic AI Railway Reservation System.
"""

import logging
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
import os
from sqlalchemy import text

logger = logging.getLogger(__name__)

from config import settings
from database import engine, SessionLocal, Base
from routes.chat import router as chat_router
from routes.tickets import router as tickets_router
from routes.auth import router as auth_router
from models import Train, Booking

# ---------------------------------------------------------------------------
# Seed data — realistic Indian trains across route pairs
# ---------------------------------------------------------------------------
TRAIN_DATA = [
    ("12951", "Mumbai Rajdhani Express", "Delhi", "Mumbai", "16:00", "08:15+1", 250, 1450.00),
    ("12953", "August Kranti Rajdhani", "Delhi", "Mumbai", "17:40", "10:55+1", 250, 1450.00),
    ("12301", "Howrah Rajdhani", "Delhi", "Kolkata", "16:55", "09:55+1", 250, 1350.00),
    ("12303", "Poorva Express", "Delhi", "Kolkata", "08:00", "20:10+1", 350, 750.00),
    ("12627", "Karnataka Express", "Delhi", "Bangalore", "22:30", "05:30+2", 300, 1100.00),
    ("12649", "Sampark Kranti Express", "Delhi", "Bangalore", "06:00", "10:30+1", 280, 980.00),
    ("12723", "Telangana Express", "Delhi", "Hyderabad", "06:25", "06:05+1", 300, 950.00),
    ("12615", "Grand Trunk Express", "Delhi", "Chennai", "18:15", "05:45+2", 280, 1250.00),
    ("12263", "Pune AC Duronto", "Delhi", "Pune", "10:55", "07:10+1", 200, 3406.00),
    ("11078", "Jhelum Express", "Delhi", "Pune", "11:30", "16:00+1", 400, 713.00),
    ("12952", "Mumbai Rajdhani Express", "Mumbai", "Delhi", "17:00", "08:35+1", 250, 1450.00),
    ("11057", "Amritsar Express", "Mumbai", "Delhi", "18:35", "23:55+1", 380, 680.00),
    ("12289", "Mumbai Duronto", "Mumbai", "Kolkata", "07:10", "05:10+1", 200, 2100.00),
    ("12161", "Lashkar Express", "Mumbai", "Hyderabad", "21:45", "11:30+1", 300, 620.00),
    ("11041", "Chennai Express", "Mumbai", "Chennai", "14:00", "14:55+1", 350, 750.00),
    ("12135", "Nagpur Express", "Mumbai", "Nagpur", "22:00", "07:15+1", 320, 480.00),
    ("12616", "Grand Trunk Express", "Chennai", "Delhi", "19:00", "05:35+2", 280, 1250.00),
    ("12658", "Chennai Mail", "Chennai", "Bangalore", "23:00", "05:45+1", 350, 380.00),
    ("12163", "Chennai Dadar Express", "Chennai", "Mumbai", "08:45", "11:35+1", 300, 780.00),
    ("12076", "Jan Shatabdi Express", "Chennai", "Hyderabad", "06:10", "15:05", 350, 545.00),
    ("12007", "Chennai Shatabdi", "Chennai", "Bangalore", "06:00", "11:00", 250, 1150.00),
    ("12628", "Karnataka Express", "Bangalore", "Delhi", "20:15", "03:10+2", 300, 1100.00),
    ("12657", "Bangalore Mail", "Bangalore", "Chennai", "22:30", "05:00+1", 350, 380.00),
    ("12779", "Goa Express", "Bangalore", "Mumbai", "23:00", "16:00+1", 300, 720.00),
    ("12785", "Kochuveli Express", "Bangalore", "Hyderabad", "23:05", "08:30+1", 280, 510.00),
    ("12724", "Telangana Express", "Hyderabad", "Delhi", "06:00", "05:45+1", 300, 950.00),
    ("12759", "Charminar Express", "Hyderabad", "Chennai", "18:15", "06:00+1", 320, 580.00),
    ("12701", "Hussainsagar Express", "Hyderabad", "Mumbai", "21:45", "11:45+1", 300, 640.00),
    ("12302", "Howrah Rajdhani", "Kolkata", "Delhi", "13:55", "17:00+1", 250, 1350.00),
    ("12860", "Gitanjali Express", "Kolkata", "Mumbai", "14:05", "16:30+1", 350, 920.00),
]

PASSENGERS = [
    "Rahul Sharma", "Priya Patel", "Arjun Mehta", "Sneha Reddy",
    "Vikram Singh", "Ananya Iyer", "Rohit Kumar", "Deepika Nair",
    "Karan Malhotra", "Sunita Rao"
]

def seed_trains():
    """
    Idempotently insert seed trains into the database.
    Checks if a train exists by its train_no before insertion.
    """
    db = SessionLocal()
    try:
        existing = {row[0] for row in db.query(Train.train_no).all()}
        train_objects = []
        for t_no, name, src, dest, dep, arr, seats, fare in TRAIN_DATA:
            if t_no not in existing:
                available = random.randint(20, seats)
                train_objects.append(Train(
                    train_no=t_no,
                    name=name,
                    source=src,
                    destination=dest,
                    departure=dep,
                    arrival=arr,
                    total_seats=seats,
                    available_seats=available,
                    fare=fare
                ))
        
        if not train_objects:
            logger.info("ℹ️  Trains table already populated — skipping seed.")
            return

        db.add_all(train_objects)
        db.commit()
        logger.info(f"✅ Seeded {len(train_objects)} trains")
    finally:
        db.close()

def seed_bookings():
    """
    Seed sample bookings spread across different trains and passengers.
    Generates 10 mock bookings with random travel dates and statuses.
    """
    db = SessionLocal()
    try:
        if db.query(Booking).count() > 0:
            print("ℹ️  Bookings already present — skipping seed.")
            return

        trains = db.query(Train).all()
        if not trains:
            return

        for i in range(10):
            train = random.choice(trains)
            passenger = PASSENGERS[i]
            travel_days = random.randint(1, 30)
            travel_date = (datetime.now() + timedelta(days=travel_days)).date()
            ticket_id = "T" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
            status = random.choice(["CONFIRMED", "CONFIRMED", "CANCELLED"]) # Weight towards confirmed
            
            booking = Booking(
                ticket_id=ticket_id,
                train_no=train.train_no,
                passenger_name=passenger,
                source=train.source,
                destination=train.destination,
                travel_date=travel_date,
                fare=train.fare,
                status=status,
                payment_status="PAID" if status == "CONFIRMED" else "CANCELLED",
                payment_reference=f"PAY-{random.randint(100000, 999999)}"
            )
            db.add(booking)
        
        db.commit()
        print(f"✅ Seeded 10 sample bookings")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Application lifespan — create tables & seed on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Railway Agent API started | env={settings.APP_ENV}")
    # In production, we don't want to drop data! 
    # Only create tables if they don't exist.
    Base.metadata.create_all(bind=engine)
    seed_trains()
    seed_bookings()
    yield


app = FastAPI(
    title="Agentic AI Railway Reservation System",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — restrict origins in production
# ---------------------------------------------------------------------------
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")

# ---------------------------------------------------------------------------
# Static Files — Serve frontend from the root
# ---------------------------------------------------------------------------
# Resolve the frontend path relative to this file
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend page."""
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "🚆 Railway Reservation Agent API is running. (Frontend folder not found)"}


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return structured JSON for all HTTP errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — log and return 500."""
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Verify the API is up and the database is reachable."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        db_status = "unreachable"
    finally:
        db.close()

    return {
        "status": "ok",
        "model": "llama-3.3-70b-versatile",
        "database": db_status,
    }

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for deployment compatibility
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=(settings.APP_ENV == "development"))

# Vercel handler
handler = Mangum(app)
