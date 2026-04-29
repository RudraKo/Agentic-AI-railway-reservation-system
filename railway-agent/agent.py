"""
agent.py - Groq-powered agentic loop for the Railway Reservation System.
Uses llama-3.3-70b-versatile with tool calling to orchestrate DB operations.
"""

import json
import logging
import re
from groq import Groq
from sqlalchemy.orm import Session

import datetime
from config import settings
from tools import search_trains, check_availability, process_payment, book_ticket, cancel_ticket

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------
client = Groq(api_key=settings.GROQ_API_KEY)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a railway reservation assistant. "
    "You help users book and cancel train tickets autonomously. "
    "CRITICAL RULE 1: When a user asks to book a ticket, use the search_trains tool to find available trains, then autonomously select the best train (most available seats, then cheapest fare) and book it using the book_ticket tool. "
    "CRITICAL RULE 2: If multiple trains are found, select the one with the most available seats; if tie, the cheapest fare. "
    "CRITICAL RULE 3: DO NOT book a ticket until the passenger name is known. Ask for it once per session if not provided. "
    "CRITICAL RULE 4: Use check_availability tool to verify seats before booking. "
    "CRITICAL RULE 5: For cancellations, use the cancel_ticket tool immediately if ticket ID is provided. "
    "Be concise and friendly. Handle multi-step workflows autonomously without further user input for selections."
)

# ---------------------------------------------------------------------------
# Tool schemas (Groq / OpenAI tool-calling format)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_trains",
            "description": (
                "Search for available trains between a source and destination "
                "on a given travel date. Call this before booking."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Departure city, e.g. 'Chennai'"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Arrival city, e.g. 'Bangalore'"
                    },
                    "travel_date": {
                        "type": "string",
                        "description": "Date of travel in YYYY-MM-DD format"
                    }
                },
                "required": ["source", "destination", "travel_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Check available seats for a specific train on a given date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "train_no": {
                        "type": "string",
                        "description": "Train number, e.g. '12607'"
                    },
                    "travel_date": {
                        "type": "string",
                        "description": "Date of travel in YYYY-MM-DD format"
                    }
                },
                "required": ["train_no", "travel_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_ticket",
            "description": (
                "Book a train ticket for a passenger on a specific train. "
                "Requires a valid train_no from search results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "train_no": {
                        "type": "string",
                        "description": "Train number, e.g. '12607'"
                    },
                    "passenger_name": {
                        "type": "string",
                        "description": "Full name of the passenger"
                    },
                    "travel_date": {
                        "type": "string",
                        "description": "Date of travel in YYYY-MM-DD format"
                    }
                },
                "required": ["train_no", "passenger_name", "travel_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_ticket",
            "description": "Cancel an existing booking using the ticket ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID to cancel, e.g. 'T3K9MZ'"
                    }
                },
                "required": ["ticket_id"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# Tool dispatcher — maps tool name → function, injects db session
# ---------------------------------------------------------------------------
def _dispatch_tool(tool_name: str, args: dict, db: Session) -> str:
    """Call the appropriate tool function and return the result as a JSON string."""
    if tool_name == "search_trains":
        result = search_trains(db=db, **args)
    elif tool_name == "check_availability":
        result = check_availability(db=db, **args)
    elif tool_name == "book_ticket":
        result = book_ticket(db=db, **args)
    elif tool_name == "cancel_ticket":
        result = cancel_ticket(db=db, **args)
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)


def _format_train_options(trains: list[dict]) -> str:
    lines = ["Available trains:"]
    for train in trains:
        lines.append(
            f"- {train['train_no']} {train['name']} ({train['departure']}-{train['arrival']}) "
            f"Seats: {train['available_seats']} Fare: {train['fare']}"
        )
    lines.append("Which train number would you like?")
    return "\n".join(lines)


def _extract_train_no(text: str) -> str | None:
    match = re.search(r"\b\d{5}\b", text)
    return match.group(0) if match else None


def _extract_passenger_name(text: str) -> str | None:
    bracket_match = re.search(r"\[Passenger name:\s*([^\]]+)\]", text, re.IGNORECASE)
    if bracket_match:
        return bracket_match.group(1).strip()

    match = re.search(r"passenger name\s+([a-zA-Z ]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_travel_date(text: str) -> str | None:
    lowered = text.lower()
    if "tomorrow" in lowered:
        return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    if "today" in lowered:
        return datetime.date.today().isoformat()

    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    return match.group(0) if match else None


def _extract_route(text: str) -> tuple[str, str] | None:
    cleaned = re.sub(r"\b(tomorrow|today|\d{4}-\d{2}-\d{2})\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    match = re.search(r"from\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+)$", cleaned, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _format_availability(train_no: str, availability: dict) -> str:
    if not availability.get("success"):
        return availability.get("message", "Could not check availability.")

    seats = availability.get("available_seats", 0)
    train_name = availability.get("train_name", "")
    travel_date = availability.get("travel_date", "")
    if seats > 0:
        return f"{seats} seat(s) are available on {train_no} {train_name} for {travel_date}."
    return f"No seats are available on {train_no} {train_name} for {travel_date}."


def _find_last_train_no(conversation_history: list) -> str | None:
    for item in reversed(conversation_history):
        if item.get("role") != "user":
            continue
        train_no = _extract_train_no(item.get("content", ""))
        if train_no:
            return train_no
    return None


def _find_last_travel_date(conversation_history: list) -> str | None:
    for item in reversed(conversation_history):
        if item.get("role") != "user":
            continue
        travel_date = _extract_travel_date(item.get("content", ""))
        if travel_date:
            return travel_date
    return None


def _extract_ticket_id(text: str) -> str | None:
    match = re.search(r"\bT[A-Z0-9]{6}\b", text.strip().upper())
    return match.group(0) if match else None


def _find_last_ticket_id(conversation_history: list) -> str | None:
    for item in reversed(conversation_history):
        ticket_id = _extract_ticket_id(item.get("content", ""))
        if ticket_id:
            return ticket_id
    return None


def _to_minutes(hhmm: str) -> int:
    try:
        hour, minute = hhmm.split(":")
        return int(hour) * 60 + int(minute)
    except Exception:
        return 24 * 60


def _pick_best_train(trains: list[dict]) -> dict | None:
    available = [train for train in trains if train.get("available_seats", 0) > 0]
    if not available:
        return None
    return min(
        available,
        key=lambda train: (
            float(train.get("fare", 0)),
            _to_minutes(train.get("departure", "23:59")),
            -(train.get("available_seats", 0)),
        ),
    )


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------
def run_agent(user_message: str, conversation_history: list, db: Session, user_id: int | None = None, session_id: str | None = None) -> dict:
    """
    Run the agentic loop for a single user turn.

    Args:
        user_message:        The latest message from the user.
        conversation_history: Accumulated message list (mutated in place).
        db:                  Active SQLAlchemy session (injected by FastAPI).

    Returns:
        {
            "response": str,                  # Final assistant text
            "conversation_history": list      # Updated history
        }
    """
    # Append latest user message
    conversation_history.append({"role": "user", "content": user_message})

    lowered = user_message.lower()
    ticket_id_match = _extract_ticket_id(user_message)

    if "cancel" in lowered:
        ticket_id = ticket_id_match or _find_last_ticket_id(conversation_history)
        if not ticket_id:
            response_text = "I couldn't find a ticket to cancel. Please share a ticket ID."
            conversation_history.append({"role": "assistant", "content": response_text})
            return {"response": response_text, "conversation_history": conversation_history}

        result = cancel_ticket(ticket_id, db, user_id=user_id)
        response_text = result.get("message", "Request processed.")
        conversation_history.append({"role": "assistant", "content": response_text})
        return {"response": response_text, "conversation_history": conversation_history}

    if "book a ticket" in lowered and "from" in lowered and "to" in lowered:
        route = _extract_route(user_message)
        if route:
            source, destination = route
            travel_date = _extract_travel_date(user_message) or datetime.date.today().isoformat()
            search_result = search_trains(source, destination, travel_date, db)
            if search_result.get("trains"):
                best_train = _pick_best_train(search_result["trains"])
                if not best_train:
                    response_text = "No seats are available on matching trains for that route."
                    conversation_history.append({"role": "assistant", "content": response_text})
                    return {"response": response_text, "conversation_history": conversation_history}

                passenger_name = _extract_passenger_name(user_message)
                if not passenger_name:
                    response_text = (
                        f"I found the best train automatically ({best_train['train_no']} {best_train['name']}). "
                        "Please provide the passenger name to complete booking."
                    )
                    conversation_history.append({"role": "assistant", "content": response_text})
                    return {"response": response_text, "conversation_history": conversation_history}

                availability = check_availability(best_train["train_no"], travel_date, db)
                if not availability.get("success"):
                    response_text = availability.get("message", "Could not verify seat availability.")
                    conversation_history.append({"role": "assistant", "content": response_text})
                    return {"response": response_text, "conversation_history": conversation_history}
                if not availability.get("can_book"):
                    response_text = _format_availability(best_train["train_no"], availability)
                    conversation_history.append({"role": "assistant", "content": response_text})
                    return {"response": response_text, "conversation_history": conversation_history}

                payment = process_payment(best_train["fare"], user_id=user_id)
                if not payment.get("success"):
                    response_text = payment.get("message", "Payment failed. Booking not completed.")
                    conversation_history.append({"role": "assistant", "content": response_text})
                    return {"response": response_text, "conversation_history": conversation_history}

                booking = book_ticket(
                    best_train["train_no"],
                    passenger_name,
                    travel_date,
                    db,
                    user_id=user_id,
                    payment_status=payment.get("payment_status", "PAID"),
                    payment_reference=payment.get("payment_reference"),
                )
                if booking.get("success") and booking.get("ticket_id"):
                    response_text = (
                        f"Ticket booked successfully on {best_train['train_no']} {best_train['name']} "
                        f"for {passenger_name}. Ticket ID: {booking['ticket_id']}. "
                        f"Payment Ref: {payment.get('payment_reference', 'N/A')}."
                    )
                else:
                    response_text = booking.get("message", "Booking failed.")
                conversation_history.append({"role": "assistant", "content": response_text})
                return {"response": response_text, "conversation_history": conversation_history}

    if "availability" in lowered or ("seats" in lowered and _extract_train_no(user_message)):
        train_no = _extract_train_no(user_message)
        travel_date = _extract_travel_date(user_message) or datetime.date.today().isoformat()
        if train_no:
            availability = check_availability(train_no, travel_date, db)
            response_text = _format_availability(train_no, availability)
            conversation_history.append({"role": "assistant", "content": response_text})
            return {"response": response_text, "conversation_history": conversation_history}
        response_text = "Please share a 5-digit train number to check availability."
        conversation_history.append({"role": "assistant", "content": response_text})
        return {"response": response_text, "conversation_history": conversation_history}

    passenger_name = _extract_passenger_name(user_message)
    if passenger_name:
        train_no = _find_last_train_no(conversation_history)
        travel_date = _find_last_travel_date(conversation_history) or datetime.date.today().isoformat()
        if train_no:
            availability = check_availability(train_no, travel_date, db)
            if not availability.get("success"):
                response_text = availability.get("message", "Could not verify seat availability.")
                conversation_history.append({"role": "assistant", "content": response_text})
                return {"response": response_text, "conversation_history": conversation_history}
            if not availability.get("can_book"):
                response_text = _format_availability(train_no, availability)
                conversation_history.append({"role": "assistant", "content": response_text})
                return {"response": response_text, "conversation_history": conversation_history}

            payment = process_payment(float(availability.get("fare", 0)), user_id=user_id)
            if not payment.get("success"):
                response_text = payment.get("message", "Payment failed. Booking not completed.")
                conversation_history.append({"role": "assistant", "content": response_text})
                return {"response": response_text, "conversation_history": conversation_history}

            booking = book_ticket(
                train_no,
                passenger_name,
                travel_date,
                db,
                user_id=user_id,
                payment_status=payment.get("payment_status", "PAID"),
                payment_reference=payment.get("payment_reference"),
            )
            if booking.get("success") and booking.get("ticket_id"):
                response_text = (
                    f"Ticket booked. Ticket ID: {booking['ticket_id']}. "
                    f"Payment Ref: {payment.get('payment_reference', 'N/A')}."
                )
            else:
                response_text = booking.get("message", "Booking failed.")
            conversation_history.append({"role": "assistant", "content": response_text})
            return {"response": response_text, "conversation_history": conversation_history}

    # Build full message list with system prompt prepended, injecting current date
    current_date = datetime.date.today().isoformat()
    dynamic_system_prompt = f"{SYSTEM_PROMPT} Today's date is {current_date}."
    messages = [{"role": "system", "content": dynamic_system_prompt}] + conversation_history

    final_response = "I'm sorry, I couldn't complete your request. Please try again."

    for iteration in range(5):  # Hard cap — prevents runaway loops
        logger.info(f"Agent loop iteration {iteration + 1}")

        import time
        response = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                break
            except Exception as groq_error:
                logger.error(f"Groq API error on iteration {iteration + 1}, attempt {attempt + 1}: {groq_error}")
                if attempt == 2:
                    return {
                        "response": (
                            "Sorry, the AI service is temporarily unavailable. "
                            "Please try again in a minute or rephrase your request."
                        ),
                        "conversation_history": conversation_history,
                    }
                time.sleep(1)

        assistant_message = response.choices[0].message

        # ── Case 1: The model wants to call tool(s) ──────────────────────
        if assistant_message.tool_calls:
            # Append the assistant's tool-call turn to messages
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            forced_response = None

            # Execute every tool call and append results
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"Executing tool: {tool_name} with args: {args}")
                tool_result = _dispatch_tool(tool_name, args, db)
                logger.info(f"Tool result: {tool_result}")

                try:
                    tool_payload = json.loads(tool_result)
                except json.JSONDecodeError:
                    tool_payload = {}

                if tool_name == "cancel_ticket":
                    message = tool_payload.get("message", "")
                    if not tool_payload.get("success") and "not found" in message.lower():
                        forced_response = message

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

            if forced_response:
                final_response = forced_response
                break

            # Continue the loop so the model can process tool results
            continue

        # ── Case 2: Model returned a plain text response ─────────────────
        final_response = assistant_message.content or final_response
        break

    # Persist the final assistant reply into conversation history
    conversation_history.append({"role": "assistant", "content": final_response})

    return {
        "response": final_response,
        "conversation_history": conversation_history
    }
