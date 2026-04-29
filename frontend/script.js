const API_BASE = "http://127.0.0.1:8000/api";
let currentSessionId = null;
let currentUserId = null;
let currentUserName = localStorage.getItem("railai_user_name") || "";
let lastUserMessage = "";
let userLat = null, userLng = null;

/**
 * Known railway stations and their coordinates for distance calculation.
 */
const STATIONS = {
    "Delhi": [28.6448, 77.2167],
    "Mumbai": [19.0760, 72.8777],
    "Chennai": [13.0827, 80.2707],
    "Bangalore": [12.9716, 77.5946],
    "Kolkata": [22.5726, 88.3639],
    "Hyderabad": [17.3850, 78.4867],
    "Pune": [18.5204, 73.8567]
};

// --- Clock Logic ---
function updateClock() {
    const now = new Date();
    const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    const clockElement = document.getElementById('clock');
    if (clockElement) {
        clockElement.textContent = `${days[now.getDay()]} ${String(now.getDate()).padStart(2,'0')} ${months[now.getMonth()]} ${now.getFullYear()}  ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    }
}
setInterval(updateClock, 1000);
updateClock();

// --- Health & Connectivity ---
/**
 * Periodically check if the backend API is reachable.
 * Updates the UI status dot accordingly.
 */
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        if(res.ok) { 
            if (dot) dot.className = 'status-dot online'; 
            if (text) text.textContent = 'SYSTEM ONLINE'; 
        }
        else throw new Error();
    } catch {
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        if (dot) dot.className = 'status-dot offline';
        if (text) text.textContent = 'BACKEND OFFLINE';
    }
}
checkHealth();

// --- Geolocation & Reverse Geocoding ---
/**
 * Detects user's current location and finds the nearest city.
 * Uses Nominatim for reverse geocoding.
 */
const locationBtn = document.getElementById('btn-location');
if (locationBtn) {
    locationBtn.addEventListener('click', () => {
        const display = document.getElementById('location-display');
        if (display) display.textContent = "Detecting...";
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(async (pos) => {
                userLat = pos.coords.latitude; userLng = pos.coords.longitude;
                try {
                    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${userLat}&lon=${userLng}&format=json`);
                    const data = await res.json();
                    const city = data.address.city || data.address.town || "Detected Area";
                    if (display) display.textContent = `📍 ${city}, ${data.address.state || ""}`;
                } catch { 
                    if (display) display.textContent = `📍 ${userLat.toFixed(2)}, ${userLng.toFixed(2)}`; 
                }
            }, () => {
                if (display) display.textContent = "Location denied";
            });
        }
    });
}

// --- Chat Communication & Agent Interaction ---
/**
 * Handles sending messages to the Agentic AI backend.
 * Manages session persistence and UI updates.
 */
const msgContainer = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const passengerNameInput = document.getElementById('passenger-name');
const sendBtn = document.getElementById('btn-send');

if (sendBtn) sendBtn.addEventListener('click', sendMessage);
if (chatInput) {
    chatInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') sendMessage(); });
}

async function sendMessage() {
    if (!chatInput) return;
    const text = chatInput.value.trim();
    if(!text) return;
    lastUserMessage = text;
    chatInput.value = '';

    appendMessage('user', text);
    const indicator = showTyping();

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: text,
                session_id: currentSessionId,
                passenger_name: passengerNameInput ? passengerNameInput.value.trim() : "",
                user_name: currentUserName
            })
        });
        const data = await res.json();
        if (indicator) indicator.remove();
        currentSessionId = data.session_id;
        currentUserId = data.user_id;
        currentUserName = data.user_name || currentUserName;
        if (currentUserName) {
            localStorage.setItem("railai_user_name", currentUserName);
        }

        await appendMessage('agent', data.response, true);
        refreshTickets();
        parseAndShowTrains(data.response);
    } catch (err) {
        if (indicator) indicator.remove();
        appendMessage('agent', "Error communicating with system.");
    }
}

function appendMessage(sender, text, animate = false) {
    if (!msgContainer) return;
    const div = document.createElement('div');
    div.className = `msg msg-${sender}`;
    const tag = document.createElement('span');
    tag.className = 'sender-tag';
    tag.textContent = sender === 'agent' ? 'RAIL·AI' : 'YOU';
    div.appendChild(tag);

    // Tool Indicator Detection
    if (sender === 'agent') {
        const low = text.toLowerCase();
        let tool = "";
        if (low.includes('searching')) tool = "[🔍 Searching trains...]";
        else if (low.includes('booking') || low.includes('booked')) tool = "[🎫 Booking ticket...]";
        else if (low.includes('cancel')) tool = "[❌ Processing cancellation...]";
        if (tool) {
            const t = document.createElement('span');
            t.className = 'tool-tag';
            t.textContent = tool;
            div.appendChild(t);
        }
    }

    const content = document.createElement('span');
    div.appendChild(content);
    msgContainer.appendChild(div);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    if (animate) {
        return new Promise(resolve => {
            let i = 0;
            const interval = setInterval(() => {
                content.textContent += text[i];
                i++;
                msgContainer.scrollTop = msgContainer.scrollHeight;
                if(i >= text.length) { clearInterval(interval); resolve(); }
            }, 12);
        });
    } else {
        content.textContent = text;
    }
}

function showTyping() {
    if (!msgContainer) return null;
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.innerHTML = `<span class="typing-label">RAIL·AI is thinking...</span><div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
    msgContainer.appendChild(div);
    msgContainer.scrollTop = msgContainer.scrollHeight;
    return div;
}

// --- Trains Logic ---
async function parseAndShowTrains(text) {
    const trainPattern = /\b\d{5}\b/g;
    const keywords = ["available", "options", "trains", "find"];
    const hasKeyword = keywords.some(k => text.toLowerCase().includes(k));
    
    if (trainPattern.test(text) || hasKeyword) {
        // Heuristic for source/dest from last message
        let source = "Chennai", dest = "Bangalore";

        const routeMatch = lastUserMessage.match(/from\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(?:\s|$)/i);
        if (routeMatch) {
            source = routeMatch[1].trim();
            dest = routeMatch[2].trim();
        } else {
            const stops = Object.keys(STATIONS);
            stops.forEach(s => {
                if (lastUserMessage.toLowerCase().includes(s.toLowerCase())) {
                    if (!lastUserMessage.toLowerCase().split(s.toLowerCase())[0].includes('to')) dest = s;
                    else source = s;
                }
            });
        }

        try {
            const res = await fetch(`${API_BASE}/trains/search?source=${source}&destination=${dest}`);
            const data = await res.json();
            renderTrains(data.trains);
        } catch (e) {}
    }
}

function renderTrains(trains) {
    const container = document.getElementById('info-content');
    if (!container) return;
    // Keep location section
    const loc = container.querySelector('.location-section');
    container.innerHTML = '';
    if (loc) container.appendChild(loc);

    if (!trains || trains.length === 0) {
        container.innerHTML += `<div class="empty-state" style="margin-top:20px">No trains found for this route.</div>`;
        return;
    }

    trains.forEach(t => {
        const card = document.createElement('div');
        card.className = 'train-card';
        
        let distHtml = "";
        if (userLat && STATIONS[t.destination]) {
            const d = haversine(userLat, userLng, STATIONS[t.destination][0], STATIONS[t.destination][1]);
            distHtml = `<div class="train-dist">📍 ~${Math.round(d)} km from you · ~${(d/55).toFixed(1)} hrs by road</div>`;
        }

        card.innerHTML = `
            <div class="train-row-1"><span class="train-name">${t.name}</span><span class="train-num">#${t.train_no}</span></div>
            <div class="train-route"><span>${t.source}</span><span>—►—</span><span>${t.destination}</span></div>
            <div class="train-times">Dep: ${t.departure} | Arr: ${t.arrival} | ₹${t.fare}</div>
            <div class="train-seats">${t.available_seats} seats available</div>
            ${distHtml}
            <div class="train-auto-note">Auto-selection enabled: best train is chosen during booking</div>
        `;
        container.appendChild(card);
    });
}

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2-lat1) * Math.PI/180;
    const dLon = (lon2-lon1) * Math.PI/180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2) * Math.sin(dLon/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// --- Ticket Management & UI Refresh ---
/**
 * Fetches the latest bookings for the current user and refreszes the UI.
 */
async function refreshTickets() {
    try {
        let url = `${API_BASE}/tickets`;
        if (currentUserId) {
            url = `${url}?user_id=${encodeURIComponent(currentUserId)}`;
        } else if (currentUserName) {
            url = `${url}?user_name=${encodeURIComponent(currentUserName)}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        const list = document.getElementById('ticket-list');
        if (!list) return;
        list.innerHTML = '';

        const active = Array.isArray(data) ? data : (data.tickets || []);
        if (active.length === 0) {
            list.innerHTML = '<div class="empty-state">No active bookings</div>';
            return;
        }

        active.forEach(t => {
            const item = document.createElement('div');
            item.className = 'ticket-item';
            item.onclick = () => showTicketModal(t);
            item.innerHTML = `
                <div class="ticket-id">${t.ticket_id}</div>
                <div class="ticket-route">${t.source} → ${t.destination}</div>
                <div class="ticket-footer">
                    <span class="ticket-date">${t.travel_date}</span>
                    <span class="badge badge-${t.status.toLowerCase()}">${t.status}</span>
                </div>
                <div class="ticket-payment">
                    Payment: <span class="badge badge-payment-${(t.payment_status || 'pending').toLowerCase()}">${t.payment_status || 'PENDING'}</span>
                </div>
            `;
            list.appendChild(item);
        });
    } catch (e) {}
}
refreshTickets();

function showTicketModal(t) {
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('modal-ticket');
    if (!modal || !overlay) return;
    modal.innerHTML = `
        <div class="modal-header">
            <div class="train-name">${t.train_name}</div>
            <div class="train-num">Train #${t.train_no}</div>
        </div>
        <div class="modal-columns">
            <div><div class="subtitle">FROM</div><div style="font-size:1.1rem">${t.source}</div><div class="train-num">${t.departure}</div></div>
            <div style="text-align:right"><div class="subtitle">TO</div><div style="font-size:1.1rem">${t.destination}</div><div class="train-num">${t.arrival}</div></div>
        </div>
        <div class="modal-id-large">${t.ticket_id}</div>
        <div style="font-size:0.8rem; border-top: 1px solid var(--border); padding-top:15px; display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <div><span class="subtitle">PASSENGER:</span><br>${t.passenger_name}</div>
            <div><span class="subtitle">DATE:</span><br>${t.travel_date}</div>
            <div><span class="subtitle">FARE:</span><br>₹${t.fare}</div>
            <div><span class="subtitle">STATUS:</span><br><span style="color:${t.status==='CONFIRMED'?'var(--green)':'var(--red)'}">${t.status}</span></div>
            <div><span class="subtitle">PAYMENT:</span><br>${t.payment_status || 'PENDING'}</div>
            <div><span class="subtitle">PAY REF:</span><br>${t.payment_reference || 'N/A'}</div>
        </div>
        ${t.status === 'CONFIRMED' ? `<button class="btn modal-cancel-btn" onclick="cancelViaChat('${t.ticket_id}')">CANCEL THIS TICKET</button>` : ''}
    `;
    overlay.style.display = 'flex';
}

window.onclick = (e) => { 
    const overlay = document.getElementById('modal-overlay');
    if(overlay && e.target.id === 'modal-overlay') overlay.style.display='none'; 
};

function cancelViaChat(id) {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.style.display='none';
    if (chatInput) {
        chatInput.value = `Cancel ticket ${id}`;
        sendMessage();
    }
}

const searchBtn = document.getElementById('btn-search');
if (searchBtn) {
    searchBtn.addEventListener('click', () => {
        if (chatInput) {
            chatInput.value = "Book a ticket from Chennai to Bangalore tomorrow";
            chatInput.focus();
        }
    });
}
