# Skylark Drones — Decision Log

**Assignment:** Drone Operations Coordinator AI Agent  
**Date:** February 2026 | **Author:** Samat

---

## 1. Key Assumptions

**Data model:** I assumed the 3 CSVs represent the canonical source of truth and treated them as database tables. All logic (conflict detection, matching) is performed at query time rather than pre-computed, to keep the system simple and always reflect the latest data.

**"Assigned" means current_assignment field is set:** A pilot/drone is considered assigned if their `current_assignment` field contains a project ID. Status field (`Available`, `Assigned`, `On Leave`) must match consistently — conflicts arise when these diverge.

**Budget is total mission budget, not daily:** `mission_budget_inr` covers the entire pilot cost for the full mission duration. Cost is computed as `daily_rate_inr × days`.

**Weather for drones:**  
- `None (Clear Sky Only)` → only flies in Sunny/Cloudy conditions  
- `IP43 (Rain)` → can fly in Rainy conditions too  
- Higher IP ratings (IP55, IP67) → all weather (future extension)

**Certifications are matched case-insensitively** and treated as comma-separated lists. A pilot needs ALL required certifications (not any one of them).

**Double-booking detection** operates on date range overlaps: if a pilot's `current_assignment` maps to a mission with overlapping dates, it's flagged as a conflict.

---

## 2. Trade-offs Chosen

### Tech Stack: FastAPI + Gemini + Next.js

**Why Gemini over OpenAI:** Already integrated with Google ecosystem (Sheets, Drive). Gemini 1.5 Flash is fast, supports native function-calling, and has a generous free tier — important for a demo with time/cost constraints.

**Why FastAPI not LangChain/CrewAI:** LangChain adds significant complexity and abstraction for diminishing returns at this scale. Direct Gemini function-calling is cleaner, more debuggable, and sufficient for 12 tools. I'd evaluate LangChain if the agent needed >30 tools or complex branching workflows.

**Why CSV fallback alongside Google Sheets:** The demo must work even without credentials.json. CSV fallback means evaluators can test without going through Google Cloud setup — reducing friction to zero.

**Why Next.js not Streamlit:** Streamlit is excellent for quick demos but produces a look-and-feel that signals "prototype." Next.js lets me deliver a polished, production-quality chat UI with proper session management, animations, and real-time status indicators — better showcases the full-stack capability.

**Stateful sessions on backend:** Conversation history is stored per session-id in memory on the FastAPI server. Trade-off: doesn't survive restarts. With more time, I'd use Redis for session persistence.

---

## 3. Urgent Reassignment — Interpretation

> *"The agent should help coordinate urgent reassignments"*

**My Interpretation:** An urgent reassignment is triggered when a pilot or drone assigned to an active mission becomes suddenly unavailable (sick, equipment failure, emergency leave). The system must:

1. **Immediately identify** all viable replacements — ranked by fit score (location match → skill match → cert match → budget fit)
2. **Surface blockers** proactively — if no clean replacement exists, flag it clearly with the constraint causing the gap
3. **Provide an action plan** — step-by-step coordinator checklist (contact pilot, update status, notify client, confirm drone)
4. **Handle both resource types** — a pilot becoming unavailable may also require swapping the drone if it's location-specific

**Implementation:** The `urgent_reassignment` tool runs `match_pilot_to_mission` or `match_drone_to_mission` with urgency framing, then appends a prioritized action checklist. The agent also proactively detects conflicts when `get_active_assignments` is called, flagging potential issues before they become urgent.

**What I'd add with more time:** A notification system (email/SMS via Twilio) triggered automatically when a HIGH severity conflict is detected, plus a "reassignment history" log sheet in Google Sheets.

---

## 4. What I'd Do Differently With More Time

**Persistent DB:** Replace CSVs with PostgreSQL. Enables proper transactions, audit trails, and multi-user concurrent writes without race conditions.

**Assignment write-back:** Currently the system reads `current_assignment` from existing data. I'd add a full write API to formally assign pilots/drones to missions — completing the full CRUD loop.

**Multi-turn memory scoped to operations:** Store not just conversation history but a "context graph" — if the agent just discussed PRJ001, the next message "update that pilot's status" should resolve the pronoun automatically.

**Conflict alerts as push notifications:** Real-time WebSocket push to the frontend when a new conflict is detected (e.g., after a status update), rather than requiring the user to ask.

**Weather API integration:** Replace the static `weather_forecast` field with a live weather API call at query time for the mission location and dates — making weather risk detection dynamic and accurate.

**Role-based access:** Coordinators can update statuses, but clients get a read-only view. Auth via NextAuth.js + service account scoping.
