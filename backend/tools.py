"""
All Gemini function-calling tool definitions and handler functions.
This is the brain of the agentic system.
"""
import json
from datetime import date
from sheets_sync import sheets
from utils import (
    parse_date, dates_overlap, calculate_pilot_cost, calculate_mission_days,
    is_weather_compatible, has_required_skills, has_required_certs,
    format_pilot, format_drone, format_mission
)

# ════════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (Gemini function declarations)
# ════════════════════════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "name": "get_pilot_roster",
        "description": (
            "Retrieve the pilot roster. Filter by skill, certification, location, or status. "
            "Use this to find available pilots, check who's on leave, or browse by expertise."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "Filter by skill e.g. 'Mapping', 'Thermal', 'Inspection'"},
                "certification": {"type": "string", "description": "Filter by certification e.g. 'DGCA', 'Night Ops'"},
                "location": {"type": "string", "description": "Filter by city e.g. 'Bangalore', 'Mumbai'"},
                "status": {"type": "string", "description": "Filter by status: 'Available', 'Assigned', 'On Leave', 'Unavailable'"},
            },
        },
    },
    {
        "name": "get_pilot_details",
        "description": "Get detailed info about a specific pilot by ID or name.",
        "parameters": {
            "type": "object",
            "properties": {
                "pilot_id": {"type": "string", "description": "Pilot ID e.g. P001"},
                "name": {"type": "string", "description": "Pilot name e.g. Arjun"},
            },
        },
    },
    {
        "name": "update_pilot_status",
        "description": (
            "Update a pilot's availability status. Valid statuses: 'Available', 'On Leave', 'Unavailable', 'Assigned'. "
            "This syncs back to Google Sheets automatically."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pilot_id": {"type": "string", "description": "Pilot ID e.g. P001"},
                "new_status": {"type": "string", "description": "New status: Available | On Leave | Unavailable | Assigned"},
                "note": {"type": "string", "description": "Optional reason for status change"},
            },
            "required": ["pilot_id", "new_status"],
        },
    },
    {
        "name": "calculate_pilot_cost",
        "description": "Calculate total cost for a pilot for a given mission or date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "pilot_id": {"type": "string", "description": "Pilot ID"},
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["pilot_id"],
        },
    },
    {
        "name": "get_drone_fleet",
        "description": (
            "Retrieve the drone fleet. Filter by capability, status, location, or weather resistance. "
            "Use this to find available drones, check maintenance status, or filter by weather suitability."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "capability": {"type": "string", "description": "e.g. 'LiDAR', 'Thermal', 'RGB'"},
                "status": {"type": "string", "description": "Available | Maintenance | Deployed"},
                "location": {"type": "string", "description": "City filter"},
                "weather_forecast": {"type": "string", "description": "Filter drones compatible with weather e.g. 'Rainy'"},
            },
        },
    },
    {
        "name": "update_drone_status",
        "description": "Update a drone's status. Syncs to Google Sheets.",
        "parameters": {
            "type": "object",
            "properties": {
                "drone_id": {"type": "string", "description": "Drone ID e.g. D001"},
                "new_status": {"type": "string", "description": "Available | Maintenance | Deployed"},
                "note": {"type": "string", "description": "Optional note"},
            },
            "required": ["drone_id", "new_status"],
        },
    },
    {
        "name": "get_missions",
        "description": "Retrieve mission/project list. Filter by location, priority, or status.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "priority": {"type": "string", "description": "Standard | High | Urgent"},
                "project_id": {"type": "string"},
            },
        },
    },
    {
        "name": "match_pilot_to_mission",
        "description": (
            "Find the best available pilot for a mission based on required skills, certifications, "
            "location, availability, and budget. Returns ranked recommendations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Mission project ID e.g. PRJ001"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "match_drone_to_mission",
        "description": (
            "Find the best available drone for a mission based on required capabilities, "
            "location, weather forecast, and maintenance status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Mission project ID"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "detect_conflicts",
        "description": (
            "Run comprehensive conflict detection across all assignments. Detects: "
            "double bookings, skill mismatches, cert mismatches, budget overruns, "
            "weather risks, and location mismatches."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Optional: check conflicts for a specific project only"},
            },
        },
    },
    {
        "name": "urgent_reassignment",
        "description": (
            "Handle urgent reassignment when a pilot or drone becomes unavailable. "
            "Finds the best available replacement and provides reassignment recommendations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project needing reassignment"},
                "reason": {"type": "string", "description": "Reason for reassignment e.g. 'Pilot sick', 'Drone malfunction'"},
                "resource_type": {"type": "string", "description": "'pilot' or 'drone'"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "get_active_assignments",
        "description": "Show all current active assignments - which pilots and drones are assigned to which projects.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ════════════════════════════════════════════════════════════════════════════════
# TOOL HANDLERS
# ════════════════════════════════════════════════════════════════════════════════

def handle_get_pilot_roster(skill=None, certification=None, location=None, status=None):
    pilots = sheets.read_pilots()
    filtered = pilots
    if skill:
        filtered = [p for p in filtered if skill.lower() in str(p.get("skills", "")).lower()]
    if certification:
        filtered = [p for p in filtered if certification.lower() in str(p.get("certifications", "")).lower()]
    if location:
        filtered = [p for p in filtered if location.lower() in str(p.get("location", "")).lower()]
    if status:
        filtered = [p for p in filtered if status.lower() == str(p.get("status", "")).lower()]

    if not filtered:
        return f"No pilots found matching criteria (skill={skill}, cert={certification}, location={location}, status={status})."

    lines = [f"Found {len(filtered)} pilot(s):\n"]
    for p in filtered:
        lines.append(format_pilot(p))
    return "\n".join(lines)


def handle_get_pilot_details(pilot_id=None, name=None):
    pilots = sheets.read_pilots()
    for p in pilots:
        if pilot_id and str(p.get("pilot_id", "")).strip() == pilot_id.strip():
            return format_pilot(p) + f"\n  Available From: {p.get('available_from', 'N/A')}\n  Assignment: {p.get('current_assignment', 'None')}"
        if name and name.lower() in str(p.get("name", "")).lower():
            return format_pilot(p) + f"\n  Available From: {p.get('available_from', 'N/A')}\n  Assignment: {p.get('current_assignment', 'None')}"
    return f"Pilot not found: {pilot_id or name}"


def handle_update_pilot_status(pilot_id: str, new_status: str, note: str = ""):
    valid = ["Available", "On Leave", "Unavailable", "Assigned"]
    if new_status not in valid:
        return f"❌ Invalid status '{new_status}'. Must be one of: {', '.join(valid)}"
    result = sheets.update_pilot_status(pilot_id, new_status, note)
    if result["success"]:
        sync_loc = result.get("synced_to", "unknown")
        return f"✅ Pilot {pilot_id} status updated to **{new_status}** (synced to {sync_loc})."
    return f"❌ Failed to update pilot status: {result.get('error')}"


def handle_calculate_pilot_cost(pilot_id: str, start_date: str = None, end_date: str = None):
    pilots = sheets.read_pilots()
    pilot = next((p for p in pilots if str(p.get("pilot_id", "")).strip() == pilot_id.strip()), None)
    if not pilot:
        return f"Pilot {pilot_id} not found."

    daily_rate = float(pilot.get("daily_rate_inr", 0))
    name = pilot.get("name", pilot_id)

    if start_date and end_date:
        days = calculate_mission_days(start_date, end_date)
        total = calculate_pilot_cost(daily_rate, start_date, end_date)
        return (
            f"💰 Cost for {name}:\n"
            f"  Daily Rate: ₹{daily_rate:,.0f}\n"
            f"  Duration: {days} day(s) ({start_date} → {end_date})\n"
            f"  **Total: ₹{total:,.0f}**"
        )
    return f"💰 {name} daily rate: ₹{daily_rate:,.0f}/day. Provide start_date and end_date for total cost."


def handle_get_drone_fleet(capability=None, status=None, location=None, weather_forecast=None):
    drones = sheets.read_drones()
    filtered = drones
    if capability:
        filtered = [d for d in filtered if capability.lower() in str(d.get("capabilities", "")).lower()]
    if status:
        filtered = [d for d in filtered if status.lower() == str(d.get("status", "")).lower()]
    if location:
        filtered = [d for d in filtered if location.lower() in str(d.get("location", "")).lower()]
    if weather_forecast:
        filtered = [d for d in filtered if is_weather_compatible(d.get("weather_resistance", ""), weather_forecast)]

    if not filtered:
        return f"No drones found matching criteria."

    lines = [f"Found {len(filtered)} drone(s):\n"]
    for d in filtered:
        lines.append(format_drone(d))
    return "\n".join(lines)


def handle_update_drone_status(drone_id: str, new_status: str, note: str = ""):
    result = sheets.update_drone_status(drone_id, new_status, note)
    if result["success"]:
        return f"✅ Drone {drone_id} status updated to **{new_status}** (synced to {result.get('synced_to', 'unknown')})."
    return f"❌ Failed: {result.get('error')}"


def handle_get_missions(location=None, priority=None, project_id=None):
    missions = sheets.read_missions()
    filtered = missions
    if location:
        filtered = [m for m in filtered if location.lower() in str(m.get("location", "")).lower()]
    if priority:
        filtered = [m for m in filtered if priority.lower() == str(m.get("priority", "")).lower()]
    if project_id:
        filtered = [m for m in filtered if project_id.upper() == str(m.get("project_id", "")).upper()]

    if not filtered:
        return "No missions found matching criteria."

    lines = [f"Found {len(filtered)} mission(s):\n"]
    for m in filtered:
        lines.append(format_mission(m))
    return "\n".join(lines)


def handle_match_pilot_to_mission(project_id: str):
    missions = sheets.read_missions()
    mission = next((m for m in missions if m.get("project_id", "").upper() == project_id.upper()), None)
    if not mission:
        return f"Mission {project_id} not found."

    pilots = sheets.read_pilots()
    req_skills = mission.get("required_skills", "")
    req_certs = mission.get("required_certs", "")
    m_location = mission.get("location", "")
    m_start = mission.get("start_date", "")
    m_end = mission.get("end_date", "")
    budget = float(mission.get("mission_budget_inr", 0))

    results = []
    for p in pilots:
        issues = []
        score = 0

        if str(p.get("status", "")).lower() not in ["available"]:
            issues.append(f"status={p.get('status')}")

        skills_ok, missing_skills = has_required_skills(p.get("skills", ""), req_skills)
        if not skills_ok:
            issues.append(f"missing skills: {missing_skills}")

        certs_ok, missing_certs = has_required_certs(p.get("certifications", ""), req_certs)
        if not certs_ok:
            issues.append(f"missing certs: {missing_certs}")

        cost = calculate_pilot_cost(float(p.get("daily_rate_inr", 0)), m_start, m_end)
        if cost > budget:
            issues.append(f"over budget (₹{cost:,.0f} > ₹{budget:,.0f})")

        # Check double booking
        if str(p.get("current_assignment", "")).strip() not in ["", "-", "None"]:
            # Check if overlaps with another mission
            for other_m in missions:
                if other_m.get("project_id") != project_id:
                    if str(p.get("current_assignment", "")) == str(other_m.get("project_id", "")):
                        if dates_overlap(m_start, m_end, other_m.get("start_date", ""), other_m.get("end_date", "")):
                            issues.append(f"double-booked with {other_m.get('project_id')}")

        location_match = str(p.get("location", "")).lower() == m_location.lower()
        if not location_match:
            issues.append(f"location mismatch ({p.get('location')} ≠ {m_location})")
        else:
            score += 10

        if not issues:
            score += 20
        if skills_ok:
            score += 5
        if certs_ok:
            score += 5

        results.append({"pilot": p, "issues": issues, "score": score, "cost": cost})

    results.sort(key=lambda x: x["score"], reverse=True)
    lines = [f"🎯 Pilot matching for **{project_id}** ({mission.get('client')} | {m_location}):\n"]
    lines.append(f"Requirements: Skills={req_skills} | Certs={req_certs} | Budget=₹{budget:,.0f} | Dates={m_start}→{m_end}\n")

    good = [r for r in results if not r["issues"]]
    bad = [r for r in results if r["issues"]]

    if good:
        lines.append("✅ **Recommended Pilots:**")
        for r in good:
            lines.append(f"  • {r['pilot'].get('name')} ({r['pilot'].get('pilot_id')}) — ₹{r['cost']:,.0f} total")
    if bad:
        lines.append("\n⚠️ **Pilots with issues:**")
        for r in bad:
            lines.append(f"  • {r['pilot'].get('name')} ({r['pilot'].get('pilot_id')}) — Issues: {'; '.join(r['issues'])}")
    if not good and not bad:
        lines.append("No pilots found.")
    return "\n".join(lines)


def handle_match_drone_to_mission(project_id: str):
    missions = sheets.read_missions()
    mission = next((m for m in missions if m.get("project_id", "").upper() == project_id.upper()), None)
    if not mission:
        return f"Mission {project_id} not found."

    drones = sheets.read_drones()
    req_skills = mission.get("required_skills", "")  # Use skills as proxy for drone capability
    m_location = mission.get("location", "")
    weather = mission.get("weather_forecast", "")

    lines = [f"🚁 Drone matching for **{project_id}** ({mission.get('client')} | {m_location} | Weather: {weather}):\n"]
    good, bad = [], []

    for d in drones:
        issues = []
        if str(d.get("status", "")).lower() != "available":
            issues.append(f"status={d.get('status')}")

        if not is_weather_compatible(d.get("weather_resistance", ""), weather):
            issues.append(f"weather incompatible ({d.get('weather_resistance')} not rated for {weather})")

        loc_match = str(d.get("location", "")).lower() == m_location.lower()
        if not loc_match:
            issues.append(f"location mismatch ({d.get('location')} ≠ {m_location})")

        # Check maintenance due
        maint = parse_date(d.get("maintenance_due", ""))
        start = parse_date(mission.get("start_date", ""))
        if maint and start and maint <= start:
            issues.append(f"maintenance overdue before mission start ({d.get('maintenance_due')})")

        if issues:
            bad.append((d, issues))
        else:
            good.append(d)

    if good:
        lines.append("✅ **Recommended Drones:**")
        for d in good:
            lines.append(f"  • {d.get('model')} ({d.get('drone_id')}) — {d.get('capabilities')} | {d.get('weather_resistance')}")
    if bad:
        lines.append("\n⚠️ **Drones with issues:**")
        for d, issues in bad:
            lines.append(f"  • {d.get('model')} ({d.get('drone_id')}) — Issues: {'; '.join(issues)}")
    if not good and not bad:
        lines.append("No drones found.")
    return "\n".join(lines)


def handle_detect_conflicts(project_id=None):
    pilots = sheets.read_pilots()
    drones = sheets.read_drones()
    missions = sheets.read_missions()

    if project_id:
        missions = [m for m in missions if m.get("project_id", "").upper() == project_id.upper()]

    conflicts = []

    for mission in missions:
        pid = mission.get("project_id", "")
        m_start = mission.get("start_date", "")
        m_end = mission.get("end_date", "")
        m_loc = mission.get("location", "")
        req_skills = mission.get("required_skills", "")
        req_certs = mission.get("required_certs", "")
        budget = float(mission.get("mission_budget_inr", 0) or 0)
        weather = mission.get("weather_forecast", "")

        # Find assigned pilot
        assigned_pilot = None
        for p in pilots:
            if str(p.get("current_assignment", "")).strip() == pid:
                assigned_pilot = p
                break

        # Find assigned drone
        assigned_drone = None
        for d in drones:
            if str(d.get("current_assignment", "")).strip() == pid:
                assigned_drone = d
                break

        if assigned_pilot:
            p = assigned_pilot
            # Skill mismatch
            skills_ok, missing = has_required_skills(p.get("skills", ""), req_skills)
            if not skills_ok:
                conflicts.append({
                    "type": "SKILL_MISMATCH", "severity": "HIGH",
                    "project": pid,
                    "message": f"Pilot {p.get('name')} lacks skills: {missing} required for {pid}"
                })

            # Cert mismatch
            certs_ok, missing_c = has_required_certs(p.get("certifications", ""), req_certs)
            if not certs_ok:
                conflicts.append({
                    "type": "CERT_MISMATCH", "severity": "HIGH",
                    "project": pid,
                    "message": f"Pilot {p.get('name')} lacks certifications: {missing_c} required for {pid}"
                })

            # Budget overrun
            cost = calculate_pilot_cost(float(p.get("daily_rate_inr", 0)), m_start, m_end)
            if budget > 0 and cost > budget:
                conflicts.append({
                    "type": "BUDGET_OVERRUN", "severity": "MEDIUM",
                    "project": pid,
                    "message": f"Pilot {p.get('name')} costs ₹{cost:,.0f} but budget is ₹{budget:,.0f} for {pid}"
                })

            # Location mismatch
            if str(p.get("location", "")).lower() != m_loc.lower():
                conflicts.append({
                    "type": "LOCATION_MISMATCH", "severity": "MEDIUM",
                    "project": pid,
                    "message": f"Pilot {p.get('name')} is in {p.get('location')} but mission is in {m_loc}"
                })

            # Double booking — check against all other missions
            for other_m in missions:
                if other_m.get("project_id") != pid:
                    if str(p.get("current_assignment", "")) == str(other_m.get("project_id", "")):
                        if dates_overlap(m_start, m_end, other_m.get("start_date", ""), other_m.get("end_date", "")):
                            conflicts.append({
                                "type": "DOUBLE_BOOKING", "severity": "CRITICAL",
                                "project": pid,
                                "message": f"Pilot {p.get('name')} double-booked: {pid} and {other_m.get('project_id')} overlap"
                            })

        if assigned_drone:
            d = assigned_drone
            # Weather risk
            if not is_weather_compatible(d.get("weather_resistance", ""), weather):
                conflicts.append({
                    "type": "WEATHER_RISK", "severity": "HIGH",
                    "project": pid,
                    "message": f"Drone {d.get('model')} ({d.get('drone_id')}) not rated for {weather} weather in {pid}"
                })

            # Drone in maintenance
            if str(d.get("status", "")).lower() == "maintenance":
                conflicts.append({
                    "type": "DRONE_MAINTENANCE", "severity": "CRITICAL",
                    "project": pid,
                    "message": f"Drone {d.get('drone_id')} assigned to {pid} but is currently in MAINTENANCE"
                })

            # Drone location mismatch
            if str(d.get("location", "")).lower() != m_loc.lower():
                conflicts.append({
                    "type": "DRONE_LOCATION_MISMATCH", "severity": "MEDIUM",
                    "project": pid,
                    "message": f"Drone {d.get('drone_id')} is in {d.get('location')} but mission is in {m_loc}"
                })

            # Pilot-drone location mismatch
            if assigned_pilot and str(assigned_pilot.get("location", "")).lower() != str(d.get("location", "")).lower():
                conflicts.append({
                    "type": "PILOT_DRONE_LOCATION_MISMATCH", "severity": "MEDIUM",
                    "project": pid,
                    "message": f"Pilot {assigned_pilot.get('name')} ({assigned_pilot.get('location')}) and Drone {d.get('drone_id')} ({d.get('location')}) are in different locations for {pid}"
                })

    if not conflicts:
        return "✅ No conflicts detected across all active assignments!"

    # Group by severity
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": []}
    for c in conflicts:
        sev = c.get("severity", "MEDIUM")
        by_sev.setdefault(sev, []).append(c)

    lines = [f"⚠️ **Conflict Report** — {len(conflicts)} issue(s) found:\n"]
    for sev, emoji in [("CRITICAL", "🔴"), ("HIGH", "🟠"), ("MEDIUM", "🟡")]:
        if by_sev.get(sev):
            lines.append(f"\n{emoji} **{sev}:**")
            for c in by_sev[sev]:
                lines.append(f"  • [{c['type']}] {c['message']}")
    return "\n".join(lines)


def handle_urgent_reassignment(project_id: str, reason: str = "", resource_type: str = "pilot"):
    missions = sheets.read_missions()
    mission = next((m for m in missions if m.get("project_id", "").upper() == project_id.upper()), None)
    if not mission:
        return f"Mission {project_id} not found."

    lines = [f"🚨 **URGENT REASSIGNMENT** for {project_id}\n"]
    if reason:
        lines.append(f"Reason: {reason}\n")

    if resource_type.lower() == "drone":
        lines.append(handle_match_drone_to_mission(project_id))
    else:
        lines.append(handle_match_pilot_to_mission(project_id))
        lines.append("\n💡 **Recommended Actions:**")
        lines.append("1. Contact the top recommended pilot immediately")
        lines.append("2. Update the original pilot's status to 'Unavailable'")
        lines.append("3. Confirm drone availability at the mission location")
        lines.append("4. Notify the client of any potential delays")
        lines.append(f"\nMission Priority: **{mission.get('priority', 'N/A')}** | Starts: {mission.get('start_date')}")
    return "\n".join(lines)


def handle_get_active_assignments():
    pilots = sheets.read_pilots()
    drones = sheets.read_drones()
    missions = sheets.read_missions()

    mission_map = {m.get("project_id"): m for m in missions}

    lines = ["📊 **Active Assignments Overview:**\n"]
    assigned_pilots = [p for p in pilots if str(p.get("current_assignment", "")).strip() not in ["", "-", "None"]]
    assigned_drones = [d for d in drones if str(d.get("current_assignment", "")).strip() not in ["", "-", "None"]]

    if assigned_pilots:
        lines.append("**Pilot Assignments:**")
        for p in assigned_pilots:
            proj = p.get("current_assignment", "")
            m = mission_map.get(proj, {})
            lines.append(f"  • {p.get('name')} ({p.get('pilot_id')}) → {proj} ({m.get('client', 'N/A')}) | {m.get('start_date')}–{m.get('end_date')}")
    else:
        lines.append("No pilots currently assigned.")

    lines.append("")
    if assigned_drones:
        lines.append("**Drone Assignments:**")
        for d in assigned_drones:
            proj = d.get("current_assignment", "")
            m = mission_map.get(proj, {})
            lines.append(f"  • {d.get('model')} ({d.get('drone_id')}) → {proj} ({m.get('client', 'N/A')})")
    else:
        lines.append("No drones currently deployed.")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ════════════════════════════════════════════════════════════════════════════════

def dispatch_tool(name: str, args: dict) -> str:
    handlers = {
        "get_pilot_roster": handle_get_pilot_roster,
        "get_pilot_details": handle_get_pilot_details,
        "update_pilot_status": handle_update_pilot_status,
        "calculate_pilot_cost": handle_calculate_pilot_cost,
        "get_drone_fleet": handle_get_drone_fleet,
        "update_drone_status": handle_update_drone_status,
        "get_missions": handle_get_missions,
        "match_pilot_to_mission": handle_match_pilot_to_mission,
        "match_drone_to_mission": handle_match_drone_to_mission,
        "detect_conflicts": handle_detect_conflicts,
        "urgent_reassignment": handle_urgent_reassignment,
        "get_active_assignments": handle_get_active_assignments,
    }
    handler = handlers.get(name)
    if not handler:
        return f"Unknown tool: {name}"
    try:
        return handler(**args)
    except Exception as e:
        return f"Tool error ({name}): {str(e)}"
