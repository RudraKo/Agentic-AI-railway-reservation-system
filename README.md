# Agentic AI Railway Reservation System

![SYSTEM ONLINE](https://img.shields.io/badge/System-ONLINE-brightgreen)
![LLM](https://img.shields.io/badge/LLM-LLaMA--3.3--70B-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Database](https://img.shields.io/badge/Database-PostgreSQL-336791)
![Deployment](https://img.shields.io/badge/Deployed-Vercel-black)

An intelligent, autonomous Agentic AI system that handles railway ticket reservations using natural language processing. Built with FastAPI, PostgreSQL, and Groq's LLaMA 3.3 model, this system allows users to seamlessly search for trains, check availability, book tickets, and process mock payments entirely through conversation.

> [!IMPORTANT]
> **Branch Notice:** The complete, production-ready codebase and active development occur on the [`main` branch](https://github.com/RudraKo/Agentic-AI-railway-reservation-system/tree/main). Please ensure you are viewing the `main` branch instead of `master` for the full code.

---

## ✨ Key Features
- **Autonomous Agentic Workflow:** The LLM does not just generate text; it actively executes Python functions to search databases, verify seat capacity, and book tickets autonomously.
- **Natural Language Payments:** Users can process mock payments simply by clicking the "PAY" button in the UI or by typing *"Pay for my ticket"* in the chat.
- **Frictionless Guest Mode:** No mandatory sign-ups. Your conversation history and ticket list are securely persisted in your browser's local storage for a seamless experience.
- **Real-Time Database:** Fully integrated with a remote Neon PostgreSQL database for persistent, multi-relational data storage.
- **Dynamic Cancellations:** Users can ask the AI to cancel their tickets, which will instantly reflect in the database, refund the seat capacity, and mark the ticket with a red `CANCELLED` badge in the UI.

---

## 🛠️ Tech Stack
| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Vanilla HTML/JS/CSS | Blazing fast, zero-dependency dark mode UI with dynamic micro-animations. |
| **Backend API** | FastAPI (Python) | High-performance async REST framework handling routing and tool dispatch. |
| **AI / LLM** | Groq (LLaMA 3.3 70B) | Ultra-low latency inference for real-time conversational agentic loops. |
| **Database** | PostgreSQL (Neon) | Relational database managed via SQLAlchemy ORM. |
| **Deployment** | Vercel | Seamlessly hosts the static frontend and executes the FastAPI backend as Serverless Functions. |

> **Why Groq instead of OpenAI?**
> OpenAI's API requires paid credits which can add up quickly during frequent agentic tool calls. Groq was chosen because it provides blazing-fast inference for open-source models like LLaMA 3.3 for free, making it ideal for testing and running autonomous agent loops without cost barriers.

---

## 🏗 Architecture & Flow of Work

The system follows a modern LLM-driven tool-calling architecture. The LLM acts as a "brain" that autonomously decides which tools to call based on the user's natural language request.

```mermaid
graph TD
    A[User / Frontend UI] -->|Natural Language Prompt| B[FastAPI Backend]
    B -->|Context + Prompt| C[Groq LLaMA-3.3-70B]
    C -.->|Tool Call Request| D{Tool Dispatcher}
    
    D -->|search_trains| E[(Neon PostgreSQL)]
    D -->|check_availability| E
    D -->|book_ticket| E
    D -->|cancel_ticket| E
    
    E -->|DB Results| D
    D -.->|Tool Results JSON| C
    C -->|Final Response| B
    B -->|Updates Chat & UI| A
```

### Conversation Flow Example
1. **User:** *"Book a ticket from Chennai to Bangalore tomorrow"*
2. **Agent:** 
   - Autonomously calls `search_trains` to find available options.
   - Evaluates trains autonomously based on seat availability and lowest fare.
   - Checks capacity via `check_availability`.
3. **Agent:** *"I found the best train... Please provide your passenger name to complete the booking."*
4. **User:** *"Rudra"*
5. **Agent:**
   - Calls `book_ticket` to finalize the reservation in `PENDING` status.
   - Responds: *"Ticket booked successfully. Your ticket ID is T123."*
6. **User:** *"Do payment"*
7. **Agent:**
   - Calls `pay_ticket` to update the database.
   - Responds: *"Payment successful. Reference: PAY-A1B2C3D4."*

---

## 📂 Folder Structure

```text
.
├── frontend/               # Vanilla JS, HTML, and CSS (Vercel static hosting)
│   ├── index.html          # Main UI entry point
│   ├── script.js           # Chat logic, API fetching, UI state management
│   └── style.css           # Premium dark-mode styling
│
├── railway_agent/          # FastAPI Backend (Vercel Serverless Functions)
│   ├── main.py             # FastAPI application and routing entry point
│   ├── agent.py            # Groq LLM integration and Agentic Loop logic
│   ├── tools.py            # Python tools (search, book, cancel, pay) exposed to LLM
│   ├── database.py         # SQLAlchemy engine and session management
│   ├── models.py           # PostgreSQL Database schemas (User, Train, Booking)
│   ├── config.py           # Environment variables (Pydantic BaseSettings)
│   ├── sessions.py         # In-memory session and conversation history manager
│   └── routes/             # REST API Endpoints
│       ├── chat.py         # /api/chat route
│       ├── tickets.py      # /api/tickets route
│       └── auth.py         # /api/register & /api/login routes
│
├── vercel.json             # Vercel deployment configuration
└── .env                    # Environment variables (not tracked in Git)
```

---

## 🚀 How to Run Locally

### 1. Prerequisites
- Python 3.10+
- A PostgreSQL Database (e.g., Neon.tech)
- Groq API Key

### 2. Installation
Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/RudraKo/Agentic-AI-railway-reservation-system.git
cd Agentic-AI-railway-reservation-system

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install backend dependencies
pip install -r railway_agent/requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the `railway_agent` directory with the following variables:
```env
GROQ_API_KEY="your_groq_api_key_here"
DATABASE_URL="postgresql://user:password@host/dbname"
APP_ENV="development"
```

### 4. Start the Application
Run the FastAPI backend server:

```bash
# From the root directory
python3 railway_agent/main.py
```
The API will start on `http://localhost:8000`.

Next, open the frontend. Since the `API_BASE` in the frontend dynamically detects if it is running locally, you can simply open `frontend/index.html` directly in your browser, or serve it using Python's built-in HTTP server:
```bash
python3 -m http.server 3000 --directory frontend
```
Then navigate to `http://localhost:3000` in your browser.

---

## 🌐 Deployment
This project is configured for seamless deployment on **Vercel** combining serverless Python functions with a static frontend.

1. Install the Vercel CLI: `npm i -g vercel`
2. Run `vercel --prod` in the project root.
3. Ensure that `GROQ_API_KEY` and `DATABASE_URL` are added to your Vercel Project Settings under Environment Variables.

---
*Developed as an advanced Agentic AI implementation.*
