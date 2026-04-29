# Detailed Setup Guide

## Prerequisites

- Python 3.9+
- Groq API Key
- PostgreSQL Instance

## Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/RudraKo/Agentic-AI-railway-reservation-system.git
   cd Agentic-AI-railway-reservation-system
   ```

2. **Backend Setup:**
   Navigate to the `railway-agent` directory and install dependencies:
   ```bash
   cd railway-agent
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   Create a `.env` file based on `.env.example`.

4. **Run the Backend:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Run the Frontend:**
   Serve the root folder using a simple HTTP server:
   ```bash
   python3 -m http.server 3000
   ```
