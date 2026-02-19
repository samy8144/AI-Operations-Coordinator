"""
Gemini AI Agent — uses prompt-based tool dispatch for broad compatibility.
Gemini returns a JSON action, we execute it and send results back.
Includes automatic retry with backoff on rate-limit (429) errors.
"""
import os
import json
import re
import time
import traceback
from dotenv import load_dotenv
import google.generativeai as genai
from tools import TOOL_DEFINITIONS, dispatch_tool

load_dotenv()


def _tool_reference():
    lines = []
    for t in TOOL_DEFINITIONS:
        params = list(t.get("parameters", {}).get("properties", {}).keys())
        lines.append(f"- {t['name']}({', '.join(params)}): {t['description'][:80]}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You are SkyBot, an expert AI Operations Coordinator for Skylark Drones.
You manage pilot rosters, drone fleet, missions, assignments, and conflict detection.

## AVAILABLE TOOLS
{_tool_reference()}

## HOW TO USE TOOLS
When the user asks something that requires data, respond with a JSON block like this:
```json
{{"action": "tool_name", "params": {{"param1": "value1"}}}}
```

You can call multiple tools sequentially. After seeing tool results, provide a clear, helpful final answer.
DO NOT use JSON action blocks in your final answer — only plain text/markdown.

## RULES
- Always call relevant tools before answering data questions
- For conflict detection questions, always call detect_conflicts
- For assignment questions, call match_pilot_to_mission or match_drone_to_mission
- For status updates, call update_pilot_status or update_drone_status
- Currency is Indian Rupees (Rs.). Today: February 2026.
- Be concise, friendly, and proactive about spotting issues.
"""

# Retry settings for rate-limit handling - Robust Backoff
_MAX_RETRIES = 6
_RETRY_DELAYS = [2, 4, 8, 16, 32, 45]  # Exponential backoff to wait out RPM limits


def _is_rate_limit(err: Exception) -> bool:
    s = str(err)
    return "429" in s or "quota" in s.lower() or "ResourceExhausted" in type(err).__name__


def _send_with_retry(fn, *args, **kwargs):
    """Call fn(*args, **kwargs) with automatic retry on rate-limit errors."""
    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if _is_rate_limit(e):
                last_err = e
                wait = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                print(f"[SkyBot] Rate limit (attempt {attempt + 1}/{_MAX_RETRIES}). Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise  # Non-rate-limit error — don't retry
    raise last_err  # All retries failed


class DroneCoordinatorAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        model_name = "models/gemini-2.0-flash"
        print(f"[SkyBot] Initializing with model: {model_name}")
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
        )
        self.conversations: dict[str, list] = {}

    def _extract_action(self, text: str):
        patterns = [
            r'action:\s*(\w+)',
            r'Action:\s*(\w+)',
            r'ACTION:\s*(\w+)'
        ]
        action = None
        for p in patterns:
            match = re.search(p, text)
            if match:
                action = match.group(1)
                break
        
        if not action:
            return None
            
        params = {}
        try:
            if "params:" in text.lower():
                param_str = text.split("params:")[-1].strip()
                if "```json" in param_str:
                    json_str = param_str.split("```json")[1].split("```")[0].strip()
                    params = json.loads(json_str)
                elif "{" in param_str:
                    json_str = "{" + param_str.split("{", 1)[1].rsplit("}", 1)[0] + "}"
                    params = json.loads(json_str)
        except:
            pass
            
        return {"action": action, "params": params}

    def chat(self, message: str, session_id: str = "default") -> str:
        history = self.conversations.get(session_id, [])

        try:
            chat_session = self.model.start_chat(history=history)
            response = _send_with_retry(chat_session.send_message, message)
            current_text = response.text
        except Exception as e:
            traceback.print_exc()
            if _is_rate_limit(e):
                return "⏳ **The AI is currently processing many requests.** I am retrying automatically. If you don't see an answer in 30 seconds, please click 'Clear Conversation' and try again."
            return f"❌ **AI Error:** {str(e)[:200]}"

        # Agentic loop
        max_iterations = 3
        for _ in range(max_iterations):
            action = self._extract_action(current_text)
            if not action or "action" not in action:
                break

            tool_name = action.get("action", "")
            tool_params = action.get("params", {})
            print(f"[SkyBot] Loop Tool: {tool_name}")

            try:
                tool_result = dispatch_tool(tool_name, tool_params)
            except Exception as e:
                tool_result = f"Error: {str(e)}"

            followup_msg = (
                f"Result: {tool_result}\nAnswer now."
            )
            try:
                response = _send_with_retry(chat_session.send_message, followup_msg)
                current_text = response.text
            except Exception as e:
                traceback.print_exc()
                break

        self.conversations[session_id] = chat_session.history

        clean = re.sub(r'```json.*?```', '', current_text, flags=re.DOTALL).strip()
        clean = re.sub(r'```.*?```', '', clean, flags=re.DOTALL).strip()
        return clean if clean else current_text.strip()

    def clear_session(self, session_id: str):
        self.conversations.pop(session_id, None)


_agent_instance = None


def get_agent() -> DroneCoordinatorAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DroneCoordinatorAgent()
    return _agent_instance
