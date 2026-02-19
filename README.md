# Skylark Drones — AI Operations Coordinator

> An agentic AI system for intelligent drone operations coordination — managing pilots, drones, missions, and conflict detection through a conversational chat interface.

## 🚀 Live Demo
> Deploy instructions below. Hosted prototype accessible via browser.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Next.js Frontend                  │
│         Dark Glassmorphism Chat UI (Port 3000)      │
│   Sidebar: Quick Actions + System Status + History  │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (fetch)
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Backend (Port 8000)             │
│  /api/chat  /api/status  /api/data/*                │
└──────────────────────┬──────────────────────────────┘
                       │ function_calling (tool loop)
┌──────────────────────▼──────────────────────────────┐
│           Google Gemini 1.5 Flash (AI Agent)        │
│  12 Tools: roster, drones, missions, conflicts      │
│  Agentic Loop: auto-selects & chains tools          │
└────────┬────────────────────────────────────────────┘
         │                       │
┌────────▼────────┐   ┌──────────▼─────────────────────┐
│  Google Sheets  │   │  CSV Fallback (data/*.csv)     │
│  (2-way sync)   │   │  Works offline / no creds      │
└─────────────────┘   └────────────────────────────────┘
```

## 📁 Project Structure

```
Skylark Drones/
├── backend/
│   ├── main.py          # FastAPI app
│   ├── agent.py         # Gemini AI agent (function calling)
│   ├── tools.py         # 12 agent tools + handlers
│   ├── sheets_sync.py   # Google Sheets 2-way sync
│   ├── utils.py         # Helpers (dates, cost, weather)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx     # Chat UI
│   │   ├── layout.tsx
│   │   ├── globals.css  # Dark glassmorphism theme
│   │   └── api/chat/route.ts
│   ├── package.json
│   └── tsconfig.json
├── data/
│   ├── pilot_roster.csv
│   ├── drone_fleet.csv
│   └── missions.csv
├── README.md
└── DECISION_LOG.md
```

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### 1. Backend Setup

```bash
cd "Skylark Drones/backend"

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: add your GEMINI_API_KEY

# Run server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd "Skylark Drones/frontend"

# Install dependencies
npm install

# Configure
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run dev server
npm run dev
```

Open **http://localhost:3000**

---

## 🔗 Google Sheets Setup (2-Way Sync)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. Create **Service Account** → Download JSON as `credentials.json` → place in `/backend/`
4. Create a Google Spreadsheet with 3 tabs: `pilot_roster`, `drone_fleet`, `missions`
5. Add headers matching the CSV columns, import data from the `/data/` CSVs
6. Share the spreadsheet with the service account email (Editor access)
7. Copy the Spreadsheet ID from the URL to `SPREADSHEET_ID` in `.env`

> **Without credentials.json:** The system automatically falls back to reading/writing the CSV files in `/data/` — everything still works!

---

## 🤖 Agent Capabilities

### Tools (12 total)
| Tool | Description |
|------|-------------|
| `get_pilot_roster` | Filter pilots by skill/cert/location/status |
| `get_pilot_details` | Get specific pilot info |
| `update_pilot_status` | Change status → syncs to Sheets |
| `calculate_pilot_cost` | Daily rate × mission days |
| `get_drone_fleet` | Filter drones by capability/weather/status |
| `update_drone_status` | Change drone status → syncs to Sheets |
| `get_missions` | List/filter missions |
| `match_pilot_to_mission` | Smart pilot matching with conflict checks |
| `match_drone_to_mission` | Smart drone matching with weather checks |
| `detect_conflicts` | Full conflict scan across all assignments |
| `urgent_reassignment` | Emergency replacement finder |
| `get_active_assignments` | Overview of all current deployments |

### Conflict Types Detected
- 🔴 **DOUBLE_BOOKING** — Pilot/drone in overlapping missions  
- 🟠 **SKILL_MISMATCH** — Pilot lacks required skills  
- 🟠 **CERT_MISMATCH** — Pilot lacks required certifications  
- 🟠 **WEATHER_RISK** — Drone not rated for mission weather  
- 🟡 **BUDGET_OVERRUN** — Pilot cost exceeds mission budget  
- 🟡 **LOCATION_MISMATCH** — Pilot/drone in wrong city  
- 🔴 **DRONE_MAINTENANCE** — Drone in maintenance but assigned  

---

## 💬 Sample Queries

```
"Show all available pilots in Bangalore"
"Find a pilot for PRJ001"
"Which drones can fly in rainy weather?"
"Detect all conflicts"
"Update Arjun's status to On Leave"
"Calculate cost for pilot P002 for PRJ002"
"Urgent reassignment for Project-A — pilot sick"
"Show active assignments"
"Match a drone to PRJ003"
```

---

## 🚀 Deployment (Railway)

The project is configured for a monorepo deployment on **Railway**.

### Automated Deployment
1. Push your code to **GitHub**.
2. Go to **[railway.app](https://railway.app)** → Create a **New Project**.
3. Select **Deploy from GitHub repo**.
4. Railway will automatically detect `railway.toml` and create both the **Backend** and **Frontend** services.

### Configuration
In the Railway dashboard, set the following:

**Backend Service:**
- `GEMINI_API_KEY`: Your Gemini API key.
- `SPREADSHEET_ID`: Your Google Sheet ID.
- `GOOGLE_CREDENTIALS_JSON`: The contents of your `credentials.json` (pasted as text).

**Frontend Service:**
- `NEXT_PUBLIC_API_URL`: The URL of your backend service (e.g., `https://backend-production.up.railway.app`).
