"""
Shared utilities: date parsing, cost calculation, data helpers.
"""
from datetime import datetime, date
from typing import Optional


def parse_date(d: str) -> Optional[date]:
    """Parse date string in multiple formats."""
    if not d or str(d).strip() in ("-", "", "None"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(d).strip(), fmt).date()
        except ValueError:
            continue
    return None


def dates_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Return True if two date ranges overlap."""
    s1, e1 = parse_date(start1), parse_date(end1)
    s2, e2 = parse_date(start2), parse_date(end2)
    if not all([s1, e1, s2, e2]):
        return False
    return s1 <= e2 and s2 <= e1


def calculate_mission_days(start_date: str, end_date: str) -> int:
    """Calculate number of days for a mission (inclusive)."""
    s, e = parse_date(start_date), parse_date(end_date)
    if not s or not e:
        return 0
    return max(1, (e - s).days + 1)


def calculate_pilot_cost(daily_rate: float, start_date: str, end_date: str) -> float:
    """Total cost = daily_rate × number of days."""
    days = calculate_mission_days(start_date, end_date)
    return daily_rate * days


def is_weather_compatible(weather_resistance: str, weather_forecast: str) -> bool:
    """
    Weather compatibility logic:
    - 'None (Clear Sky Only)' → only flies in Sunny/Clear/Cloudy (not Rainy/Stormy)
    - 'IP43 (Rain)' → can fly in Rainy conditions too
    - 'IP55' / 'IP67' → can fly in all conditions
    """
    if not weather_resistance or not weather_forecast:
        return True

    resistance = str(weather_resistance).lower()
    forecast = str(weather_forecast).lower()

    rainy_conditions = ["rainy", "rain", "stormy", "storm", "heavy rain"]
    is_rainy = any(r in forecast for r in rainy_conditions)

    if is_rainy:
        return "ip43" in resistance or "ip55" in resistance or "ip67" in resistance
    return True


def has_required_skills(pilot_skills: str, required_skills: str) -> tuple[bool, list[str]]:
    """Check if pilot has all required skills. Returns (ok, missing_skills)."""
    pilot_set = {s.strip().lower() for s in str(pilot_skills).split(",")}
    required_set = {s.strip().lower() for s in str(required_skills).split(",")}
    missing = [s for s in required_set if s not in pilot_set]
    return len(missing) == 0, missing


def has_required_certs(pilot_certs: str, required_certs: str) -> tuple[bool, list[str]]:
    """Check if pilot has all required certifications. Returns (ok, missing_certs)."""
    pilot_set = {c.strip().lower() for c in str(pilot_certs).split(",")}
    required_set = {c.strip().lower() for c in str(required_certs).split(",")}
    missing = [c for c in required_set if c not in pilot_set]
    return len(missing) == 0, missing


def format_pilot(p: dict) -> str:
    """Human-readable pilot summary."""
    return (
        f"🧑‍✈️ {p.get('name', 'Unknown')} ({p.get('pilot_id', '')}) | "
        f"Location: {p.get('location', 'N/A')} | "
        f"Status: {p.get('status', 'N/A')} | "
        f"Skills: {p.get('skills', 'N/A')} | "
        f"Certs: {p.get('certifications', 'N/A')} | "
        f"Rate: ₹{p.get('daily_rate_inr', 'N/A')}/day"
    )


def format_drone(d: dict) -> str:
    """Human-readable drone summary."""
    return (
        f"🚁 {d.get('model', 'Unknown')} ({d.get('drone_id', '')}) | "
        f"Location: {d.get('location', 'N/A')} | "
        f"Status: {d.get('status', 'N/A')} | "
        f"Capabilities: {d.get('capabilities', 'N/A')} | "
        f"Weather: {d.get('weather_resistance', 'N/A')} | "
        f"Maintenance Due: {d.get('maintenance_due', 'N/A')}"
    )


def format_mission(m: dict) -> str:
    """Human-readable mission summary."""
    return (
        f"📋 {m.get('project_id', '')} - {m.get('client', 'Unknown')} | "
        f"Location: {m.get('location', 'N/A')} | "
        f"Skills: {m.get('required_skills', 'N/A')} | "
        f"Certs: {m.get('required_certs', 'N/A')} | "
        f"Dates: {m.get('start_date', 'N/A')} → {m.get('end_date', 'N/A')} | "
        f"Priority: {m.get('priority', 'N/A')} | "
        f"Budget: ₹{m.get('mission_budget_inr', 'N/A')} | "
        f"Weather: {m.get('weather_forecast', 'N/A')}"
    )
