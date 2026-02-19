import os
import json
import pandas as pd
from datetime import datetime, date
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Fallback CSV paths (relative to backend/)
CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _get_csv_path(name: str) -> str:
    return os.path.join(CSV_DIR, f"{name}.csv")


class SheetsSync:
    def __init__(self):
        self.client = None
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.sh = None  # Cache for spreadsheet object
        self._worksheets = {}  # Cache for worksheet objects
        self._init_client()

    def _init_client(self):
        # 1. Try loading from environment variable (best for cloud like Railway/Render)
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
                self.client = gspread.authorize(creds)
                print("✅ Google Sheets initialized from ENV JSON")
                return
            except Exception as e:
                print(f"⚠️  Failed to init Sheets from GOOGLE_CREDENTIALS_JSON: {e}")

        # 2. Fallback to physical file
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        if os.path.exists(creds_path):
            try:
                creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
                self.client = gspread.authorize(creds)
                print("✅ Google Sheets initialized from credentials.json")
            except Exception as e:
                print(f"⚠️  Google Sheets file init failed: {e}. Using CSV fallback.")
        else:
            print("⚠️  No credentials found (checking ENV or file). Using CSV fallback.")

    def _get_worksheet(self, tab_name: str):
        # 1. Return from cache if available
        if tab_name in self._worksheets:
            return self._worksheets[tab_name]

        # Lazy reconnect — try to init if client is still None
        if not self.client:
            self._init_client()
        if not self.client or not self.spreadsheet_id:
            return None
        try:
            # 2. Open spreadsheet if not already cached
            if not self.sh:
                self.sh = self.client.open_by_key(self.spreadsheet_id)
            
            # 3. Get worksheet and cache it
            ws = self.sh.worksheet(tab_name)
            self._worksheets[tab_name] = ws
            return ws
        except Exception as e:
            print(f"⚠️  Could not open worksheet '{tab_name}': {e}")
            # Reset cache if error occurs (could be token expired or network issue)
            self.sh = None
            self._worksheets = {}
            return None

    # ── READ METHODS ──────────────────────────────────────────────────────────

    def read_pilots(self) -> list[dict]:
        ws = self._get_worksheet("pilot_roster")
        if ws:
            try:
                records = ws.get_all_records()
                if records:
                    return records
            except Exception as e:
                print(f"⚠️  Sheets read error: {e}")
        # CSV fallback
        try:
            df = pd.read_csv(_get_csv_path("pilot_roster"))
            return df.fillna("").to_dict("records")
        except Exception:
            return []

    def read_drones(self) -> list[dict]:
        ws = self._get_worksheet("drone_fleet")
        if ws:
            try:
                records = ws.get_all_records()
                if records:
                    return records
            except Exception as e:
                print(f"⚠️  Sheets read error: {e}")
        try:
            df = pd.read_csv(_get_csv_path("drone_fleet"))
            return df.fillna("").to_dict("records")
        except Exception:
            return []

    def read_missions(self) -> list[dict]:
        ws = self._get_worksheet("missions")
        if ws:
            try:
                records = ws.get_all_records()
                if records:
                    return records
            except Exception as e:
                print(f"⚠️  Sheets read error: {e}")
        try:
            df = pd.read_csv(_get_csv_path("missions"))
            return df.fillna("").to_dict("records")
        except Exception:
            return []

    # ── WRITE METHODS ─────────────────────────────────────────────────────────

    def update_pilot_status(self, pilot_id: str, new_status: str, note: str = "") -> dict:
        """Update a pilot's status in Google Sheets and local cache."""
        pilots = self.read_pilots()
        updated = False
        for p in pilots:
            if str(p.get("pilot_id", "")).strip() == pilot_id.strip():
                p["status"] = new_status
                if note:
                    p["note"] = note
                updated = True
                break

        if not updated:
            return {"success": False, "error": f"Pilot {pilot_id} not found"}

        # Write back to Sheets
        ws = self._get_worksheet("pilot_roster")
        if ws:
            try:
                all_data = ws.get_all_values()
                headers = all_data[0]
                status_col = headers.index("status") + 1  # 1-indexed
                id_col = headers.index("pilot_id") + 1

                for i, row in enumerate(all_data[1:], start=2):
                    if row[id_col - 1] == pilot_id:
                        ws.update_cell(i, status_col, new_status)
                        return {"success": True, "synced_to": "Google Sheets", "pilot_id": pilot_id, "new_status": new_status}
            except Exception as e:
                print(f"⚠️  Sheets write error: {e}")

        # CSV fallback write
        try:
            df = pd.read_csv(_get_csv_path("pilot_roster"))
            df.loc[df["pilot_id"] == pilot_id, "status"] = new_status
            df.to_csv(_get_csv_path("pilot_roster"), index=False)
            return {"success": True, "synced_to": "CSV (offline)", "pilot_id": pilot_id, "new_status": new_status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_drone_status(self, drone_id: str, new_status: str, note: str = "") -> dict:
        """Update a drone's status in Google Sheets."""
        ws = self._get_worksheet("drone_fleet")
        if ws:
            try:
                all_data = ws.get_all_values()
                headers = all_data[0]
                status_col = headers.index("status") + 1
                id_col = headers.index("drone_id") + 1

                for i, row in enumerate(all_data[1:], start=2):
                    if row[id_col - 1] == drone_id:
                        ws.update_cell(i, status_col, new_status)
                        return {"success": True, "synced_to": "Google Sheets", "drone_id": drone_id, "new_status": new_status}
                return {"success": False, "error": f"Drone {drone_id} not found in sheet"}
            except Exception as e:
                print(f"⚠️  Sheets write error: {e}")

        # CSV fallback
        try:
            df = pd.read_csv(_get_csv_path("drone_fleet"))
            df.loc[df["drone_id"] == drone_id, "status"] = new_status
            df.to_csv(_get_csv_path("drone_fleet"), index=False)
            return {"success": True, "synced_to": "CSV (offline)", "drone_id": drone_id, "new_status": new_status}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
sheets = SheetsSync()
