import streamlit as st
import os
import sys
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path so we can import our modules
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)

from agent import get_agent
from sheets_sync import sheets

# Load environment variables
load_dotenv(os.path.join(backend_path, ".env"))

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Skylark Drones AI Coordinator",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Premium Dark Theme Adjustments */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #e2e8f0;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(59, 130, 246, 0.2);
    }
    
    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* Chat Bubbles */
    .stChatMessage {
        background: rgba(30, 41, 59, 0.4) !important;
        border: 1px solid rgba(59, 130, 246, 0.1) !important;
        border-radius: 15px !important;
    }
    
    .stChatMessage[data-testid="stChatMessageUser"] {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
        color: white !important;
    }

    /* Status Indicators */
    .status-dot {
        height: 8px;
        width: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    .status-online { background-color: #10b981; box-shadow: 0 0 10px #10b981; }
    .status-offline { background-color: #f59e0b; box-shadow: 0 0 10px #f59e0b; }

    /* Titles */
    h1, h2, h3 {
        background: linear-gradient(to right, #3b82f6, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """👋 **Welcome to Skylark Drones AI Operations Coordinator!**

I'm **SkyBot**, your intelligent drone operations assistant. I can help you with:

- 🧑‍✈️ **Pilot Management** — Query availability, skills, certifications & update statuses
- 🚁 **Drone Fleet** — Check availability, weather compatibility & maintenance status  
- 📋 **Mission Matching** — Find optimal pilot+drone combos for each project
- ⚠️ **Conflict Detection** — Spot double-bookings, budget overruns & weather risks
- 🚨 **Urgent Reassignment** — Handle emergency crew changes instantly

What would you like to do?"""
        }
    ]

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🚁 Skylark Drones")
    st.caption("AI Operations Coordinator")
    st.divider()
    
    # System Status
    st.markdown("#### System Status")
    
    try:
        pilots = sheets.read_pilots()
        drones = sheets.read_drones()
        missions = sheets.read_missions()
        gs_connected = sheets.client is not None
        
        status_class = "status-online" if gs_connected else "status-offline"
        status_text = "Google Sheets Synced" if gs_connected else "Local CSV Mode"
        
        st.markdown(f"""
            <div class="glass-card">
                <p style='font-size: 0.8rem; color: #94a3b8; margin-bottom: 10px;'>
                    <span class='status-dot {status_class}'></span>{status_text}
                </p>
                <div style='display: flex; justify-content: space-between; font-size: 0.85rem;'>
                    <span>✈️ Pilots</span><span style='color: #60a5fa;'>{len(pilots)}</span>
                </div>
                <div style='display: flex; justify-content: space-between; font-size: 0.85rem;'>
                    <span>🚁 Drones</span><span style='color: #22d3ee;'>{len(drones)}</span>
                </div>
                <div style='display: flex; justify-content: space-between; font-size: 0.85rem;'>
                    <span>📋 Missions</span><span style='color: #c084fc;'>{len(missions)}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error loading system status: {e}")

    st.divider()
    
    # Quick Actions
    st.markdown("#### Quick Actions")
    queries = [
        "Show all available pilots",
        "Detect all conflicts",
        "Which drones can fly in Rainy weather?",
        "Show active assignments",
        "Update pilot P001 status to On Leave"
    ]
    
    for q in queries:
        if st.button(q, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": q})
            # Trigger chatbot response
            ag = get_agent()
            with st.spinner("SkyBot is thinking..."):
                response = ag.chat(q, session_id=st.session_state.session_id)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    st.divider()
    if st.button("🗑 Clear Conversation", type="secondary", use_container_width=True):
        get_agent().clear_session(st.session_state.session_id)
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# --- MAIN CHAT UI ---
st.markdown("## SkyBot — Operations Coordinator")
st.caption("Powered by Gemini 2.0 Flash")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about pilots, drones, missions..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get assistant response
    ag = get_agent()
    with st.chat_message("assistant"):
        with st.spinner("SkyBot is thinking..."):
            try:
                response = ag.chat(prompt, session_id=st.session_state.session_id)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Connection Error: {e}")
                st.markdown("Please check your GEMINI_API_KEY and internet connection.")

# Footer
st.markdown("---")
st.caption("© 2026 Skylark Drones AI · All data syncs to Google Sheets")
