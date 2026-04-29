# Agentic AI Railway Reservation System

## Overview
The Agentic AI Railway Reservation System is a sophisticated platform designed to automate the train booking and cancellation process using large language models (LLMs).

- [Architecture Details](docs/architecture.md)
- [Detailed Setup Guide](docs/setup.md)

## Architecture and Technologies

### Backend
*   **FastAPI:** High-performance web framework for building the RESTful API.
*   **SQLAlchemy:** Object-Relational Mapping (ORM) for database interactions.
*   **Groq (Llama-3.3-70b-versatile):** The primary inference engine for the agentic reasoning loop and tool-calling capabilities.
*   **Pydantic Settings:** Management of environment variables and application configurations.
*   **PyJWT & Passlib:** Secure user authentication and password hashing.
*   **Neon PostgreSQL:** Serverless cloud database for persistent storage.

### Frontend
*   **HTML5/CSS3:** Modern, responsive interface with a terminal-inspired aesthetic.
## Features

- **Autonomous Agentic Workflow:** Uses LLMs to interpret natural language and execute train reservation tasks.
- **Real-time Session Management:** Tracks user context and booking state across multiple interactions.
- **Dynamic Geolocation:** Automatically detects the nearest railway stations using reverse geocoding.
- **Terminal-Inspired UI:** A modern, sleek dark-mode interface for a premium user experience.
- **Secure Authentication:** Implements JWT-based user identity and secure password hashing.
- **Database Persistence:** Scalable PostgreSQL integration for managing trains, bookings, and users.
- **Automated Seeding:** Self-populating database with realistic Indian train data on startup.

## Local Development Setup

### Prerequisites
*   Python 3.9 or higher
*   A Groq API Key
*   A PostgreSQL database (Neon DB recommended)

### Backend Configuration
1.  Navigate to the backend directory:
    ```bash
    cd railway-agent
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure environment variables in a `.env` file:
    ```env
    GROQ_API_KEY=your_api_key_here
    DATABASE_URL=your_postgresql_url_here
    SECRET_KEY=your_random_secret_string
    ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
    APP_ENV=development
    ```
5.  Start the FastAPI server:
    ```bash
    uvicorn main:app --host 127.0.0.1 --port 8000
    ```

### Frontend Configuration
1.  Navigate to the frontend directory.
2.  Serve the files using a local web server:
    ```bash
    python3 -m http.server 3000
    ```
3.  Access the application in your browser at `http://localhost:3000`.

## Operational Flow

### 1. System Initialization
Upon launching the application, the system performs a health check to verify backend connectivity and database status. The sidebar on the right allows the user to detect their current location, which calculates distances to the nearest railway hubs.

### 2. User Authentication and Identity
To initiate the agentic flow, the user should provide their name in the input field. This identity is used to track bookings and personal tickets across sessions.

### 3. Natural Language Booking
The user can interact with the agent via the chat interface. Example commands include:
*   "Search for trains from Delhi to Mumbai tomorrow."
*   "Book a ticket for the Rajdhani Express on Friday."

The agent autonomously performs the following steps:
*   Parses the source, destination, and date.
*   Searches the database for matching trains.
*   Selects the optimal train based on seat availability and fare.
*   Validates passenger data and processes a simulated payment.
*   Returns a unique Ticket ID upon success.

### 4. Ticket Management
Confirmed tickets appear in the "My Tickets" panel on the left. Clicking on a ticket displays a digital pass with full journey details, including departure times, platforms, and payment references.

### 5. Autonomous Cancellation
A user can cancel a ticket either through the UI button or by telling the agent: "Cancel my ticket [ID]". The agent verifies the ticket ownership, updates the database status, and restores seat availability for other users.

## Security Considerations
*   **JWT Authentication:** All sensitive operations are protected via JSON Web Tokens.
*   **Input Sanitization:** The agent uses rigorous schema validation to prevent LLM hallucinations or improper data entry.
*   **Production Hardening:** The system is configured to manage CORS policies and environment-specific configurations to ensure a secure transition from development to production.
