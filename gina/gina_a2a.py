"""
Gina A2A - User profile management agent.
Handles user queries and registration via structured protocol.
"""

import json
import logging
import os
from typing import Any, Dict

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types

from gina_tools import get_user_profile as _db_get_user_profile
from gina_tools import save_user_profile as _db_save_user_profile
from gina_utils import (
    cleanup_stale_registrations,
    create_profile_from_collected_data,
    create_registration_state,
    delete_registration,
    generate_conversation_id,
    generate_user_id,
    get_registration_state,
    is_affirmative,
    is_skip_request,
    update_registration_activity,
    validate_name,
    validate_phone,
)
from iris_gina_protocol import GinaRequest, GinaResponse

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s [%(levelname)s]: %(message)s'
)
logger = logging.getLogger("gina_a2a")

API_KEY = os.environ.get("GEMINI_API_KEY", "")

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

efficient_model = Gemini(
    model="gemini-2.5-flash",
    api_key=API_KEY,
    retry_options=retry_config,
)

# ═══════════════════════════════════════════════════════════════════
# DETERMINISTIC TOOLS
# ═══════════════════════════════════════════════════════════════════

def gina_get_user_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Queries a user profile by their ID.
    
    Args:
        args: {"action": "get_profile", "user_id": "<id>"}
             (can come as dict or JSON string)
    
    Returns:
        {"type": "profile_found", "payload": {"profile": {...}}}
        or {"type": "profile_not_found"}
        or {"type": "error", "payload": {"reason": "...", "message": "..."}}
    """
    try:
        cleanup_stale_registrations()
        
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {args}")
                return {
                    "type": "error",
                    "payload": {
                        "reason": "invalid_json",
                        "message": "The argument must be valid JSON"
                    }
                }
        
        user_id = args.get("user_id") if isinstance(args, dict) else None
        
        if not user_id:
            logger.error("get_user_profile without user_id")
            return {
                "type": "error",
                "payload": {
                    "reason": "missing_user_id",
                    "message": "user_id is required"
                }
            }

        logger.info(f"-> GET_PROFILE: user_id={user_id}")
        result = _db_get_user_profile({"user_id": str(user_id)})

        if isinstance(result, dict) and result.get("exists"):
            profile = result.get("profile", {})
            logger.info(f"<- PROFILE_FOUND: user_id={user_id}, name={profile.get('name')}")
            return {
                "type": "profile_found",
                "payload": {"profile": profile}
            }
        else:
            logger.info(f"<- PROFILE_NOT_FOUND: user_id={user_id}")
            return {"type": "profile_not_found"}
            
    except Exception as e:
        logger.exception("Error in gina_get_user_profile")
        return {
            "type": "error",
            "payload": {
                "reason": "exception",
                "message": str(e)
            }
        }


def gina_handle_registration_step(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles a step in the conversational registration flow.
    
    Args:
        args: {
            "action": "start_registration" | "continue_registration",
            "conversation_id": "<id>",  # Only for continue
            "user_message": "<text>"   # Only for continue
        }
        (can come as dict or JSON string)
    
    Returns:
        {"type": "registration_started", "payload": {"conversation_id": "...", "prompt": "..."}}
        {"type": "ask_user_data", "payload": {"conversation_id": "...", "field": "...", "prompt": "..."}}
        {"type": "confirm_data", "payload": {"conversation_id": "...", "summary": "...", "prompt": "..."}}
        {"type": "registration_complete", "payload": {"user_id": "...", "profile": {...}}}
        {"type": "error", "payload": {"reason": "...", "message": "..."}}
    """
    try:
        if isinstance(args, str):
            logger.info(f"-> REGISTRATION_STEP received STRING: {args}")
            try:
                args = json.loads(args)
                logger.info(f"-> REGISTRATION_STEP parsed: {args}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {args}")
                return {
                    "type": "error",
                    "payload": {
                        "reason": "invalid_json",
                        "message": "The argument must be valid JSON"
                    }
                }
        else:
            logger.info(f"-> REGISTRATION_STEP received DICT: {args}")
        
        action = args.get("action") if isinstance(args, dict) else None
        
        if not action:
            logger.error(f"'action' not found in args: {args}")
            return {
                "type": "error",
                "payload": {
                    "reason": "missing_action",
                    "message": "The 'action' field is required"
                }
            }
        
        # ────────────────────────────────────────────────────────────
        # 1. START REGISTRATION
        # ────────────────────────────────────────────────────────────
        if action == "start_registration":
            conv_id = generate_conversation_id()
            create_registration_state(conv_id)
            
            logger.info(f"-> START_REGISTRATION: conversation_id={conv_id}")
            
            response = {
                "type": "registration_started",
                "payload": {
                    "conversation_id": conv_id,
                    "prompt": "Hi, I'm Gina. To register you I need some information. What's your full name?"
                }
            }
            
            logger.info(f"<- REGISTRATION_STARTED: {json.dumps(response, ensure_ascii=False)}")
            return response
        
        # ────────────────────────────────────────────────────────────
        # 2. CONTINUE REGISTRATION
        # ────────────────────────────────────────────────────────────
        if action == "continue_registration":
            conv_id = args.get("conversation_id")
            user_msg = args.get("user_message")
            
            if not conv_id:
                logger.error("continue_registration without conversation_id")
                return {
                    "type": "error",
                    "payload": {
                        "reason": "missing_conversation_id",
                        "message": "conversation_id is required to continue"
                    }
                }
            
            logger.info(f"-> CONTINUE_REGISTRATION: conversation_id={conv_id}, message='{user_msg}'")
            
            state = get_registration_state(conv_id)
            
            if not state:
                logger.warning(f"Conversation not found: {conv_id}")
                return {
                    "type": "error",
                    "payload": {
                        "reason": "conversation_not_found",
                        "message": "Conversation not found or expired. Please start registration again."
                    }
                }
            
            update_registration_activity(conv_id)
            
            stage = state.get("stage", "started")
            collected = state.setdefault("collected", {})
            
            # ────────────────────────────────────────────────────────
            # STATE MACHINE
            # ────────────────────────────────────────────────────────
            
            # STATE: STARTED (first message after starting)
            if stage == "started":
                state["stage"] = "awaiting_name"
                stage = "awaiting_name"
                logger.info(f"Stage changed from 'started' to 'awaiting_name'")
                
            # STATE: AWAITING_NAME
            if stage == "awaiting_name":
                name = validate_name(user_msg) if user_msg else None
                
                if name:
                    collected["name"] = name
                    state["stage"] = "awaiting_phone"
                    
                    logger.info(f"<- ASK_PHONE: name={name}")
                    return {
                        "type": "ask_user_data",
                        "payload": {
                            "conversation_id": conv_id,
                            "field": "phone",
                            "prompt": f"Perfect, {name}. Can you give me your phone number? (or type 'skip' if you prefer not to share it)"
                        }
                    }
                else:
                    logger.warning(f"Invalid name: '{user_msg}'")
                    return {
                        "type": "ask_user_data",
                        "payload": {
                            "conversation_id": conv_id,
                            "field": "name",
                            "prompt": "I couldn't understand your name well. Please type your full name (e.g: John Smith)."
                        }
                    }
            
            # STATE: AWAITING_PHONE
            if stage == "awaiting_phone":
                if is_skip_request(user_msg or ""):
                    collected["phone"] = None
                    logger.info("User skipped phone")
                else:
                    phone = validate_phone(user_msg) if user_msg else None
                    collected["phone"] = phone
                    
                    if not phone and user_msg:
                        logger.warning(f"Invalid phone: '{user_msg}'")
                
                state["stage"] = "confirm"
                
                name = collected.get('name', '(no name)')
                phone = collected.get('phone')
                
                if phone:
                    summary = f"Confirm your data:\n\n- Name: {name}\n- Phone: {phone}"
                else:
                    summary = f"Confirm your data:\n\n- Name: {name}\n- Phone: (skipped)"
                
                logger.info(f"<- CONFIRM_DATA: {summary.replace(chr(10), ' ')}")
                return {
                    "type": "confirm_data",
                    "payload": {
                        "conversation_id": conv_id,
                        "summary": summary,
                        "prompt": f"{summary}\n\nAll correct? (yes / no)"
                    }
                }
            
            # STATE: CONFIRM
            if stage == "confirm":
                if is_affirmative(user_msg or ""):
                    # Confirmed -> generate ID and save
                    user_id = generate_user_id()
                    profile = create_profile_from_collected_data(collected)
                    
                    # Persist in DB
                    save_result = _db_save_user_profile({
                        "user_id": user_id,
                        "profile": profile
                    })
                    
                    if save_result.get("saved"):
                        logger.info(f"<- REGISTRATION_COMPLETE: user_id={user_id}, name={profile.get('name')}")
                        
                        # Clean up state
                        delete_registration(conv_id)
                        
                        return {
                            "type": "registration_complete",
                            "payload": {
                                "conversation_id": conv_id,
                                "user_id": user_id,
                                "profile": profile
                            }
                        }
                    else:
                        logger.error(f"Error saving profile: {save_result}")
                        return {
                            "type": "error",
                            "payload": {
                                "reason": "save_failed",
                                "message": "There was an error saving your profile. Please try again."
                            }
                        }
                else:
                    # User said no -> restart
                    logger.info("User rejected confirmation, restarting")
                    state["stage"] = "awaiting_name"
                    state["collected"] = {}
                    
                    return {
                        "type": "ask_user_data",
                        "payload": {
                            "conversation_id": conv_id,
                            "field": "name",
                            "prompt": "Perfect, let's start over. What is your full name?"
                        }
                    }
            
            # STATE: DONE
            if stage == "done":
                return {
                    "type": "info",
                    "payload": {
                        "message": "This registration was already completed previously."
                    }
                }
            
            # UNKNOWN STATE
            logger.error(f"Unknown stage: {stage}")
            return {
                "type": "error",
                "payload": {
                    "reason": "unknown_stage",
                    "message": f"Invalid conversation state: {stage}"
                }
            }
        
        # UNKNOWN ACTION
        logger.error(f"Unknown action: {action}")
        return {
            "type": "error",
            "payload": {
                "reason": "unknown_action",
                "message": f"Action not recognized: {action}"
            }
        }

    except Exception as e:
        logger.exception("Error in gina_handle_registration_step")
        return {
            "type": "error",
            "payload": {
                "reason": "exception",
                "message": str(e)
            }
        }


# ═══════════════════════════════════════════════════════════════════
# GINA AGENT
# ═══════════════════════════════════════════════════════════════════

tools = [
    FunctionTool(gina_get_user_profile),
    FunctionTool(gina_handle_registration_step),
]

GINA_INSTRUCTIONS = """
You are **Gina**, a microservice for user profile management.

IMPORTANT: You MUST ALWAYS call ONE of your two tools and return its result.

═══════════════════════════════════════════════════════════════════
YOUR TOOLS
═══════════════════════════════════════════════════════════════════

You have only 2 available tools:

1. gina_get_user_profile - To check if a profile exists
2. gina_handle_registration_step - For EVERYTHING related to registration

═══════════════════════════════════════════════════════════════════
DECISION: WHICH TOOL TO USE?
═══════════════════════════════════════════════════════════════════

When you receive a message, check the "action" field:

If action contains "get_profile":
   -> Use gina_get_user_profile

If action contains "start_registration" OR "continue_registration":
   -> Use gina_handle_registration_step

ALWAYS pass the COMPLETE JSON message you received as argument to the tool.

═══════════════════════════════════════════════════════════════════
STEP-BY-STEP EXAMPLES
═══════════════════════════════════════════════════════════════════

EXAMPLE 1: Profile query
---
Message received: {"action": "get_profile", "user_id": "12346"}

Reasoning:
- The action is "get_profile"
- I must use gina_get_user_profile
- Pass the COMPLETE JSON I received

Action: Call gina_get_user_profile with {"action": "get_profile", "user_id": "12346"}

Tool returns: {"type": "profile_not_found"}

My final response: {"type": "profile_not_found"}
---

EXAMPLE 2: Start registration
---
Message received: {"action": "start_registration"}

Reasoning:
- The action is "start_registration"
- I must use gina_handle_registration_step
- Pass the COMPLETE JSON I received

Action: Call gina_handle_registration_step with {"action": "start_registration"}

Tool returns: {"type": "registration_started", "payload": {"conversation_id": "xyz789", "prompt": "What's your full name?"}}

My final response: {"type": "registration_started", "payload": {"conversation_id": "xyz789", "prompt": "What's your full name?"}}
---

EXAMPLE 3: Continue registration
---
Message received: {"action": "continue_registration", "conversation_id": "xyz789", "user_message": "Maria Lopez"}

Reasoning:
- The action is "continue_registration"
- I must use gina_handle_registration_step
- Pass the COMPLETE JSON

Action: Call gina_handle_registration_step with {"action": "continue_registration", "conversation_id": "xyz789", "user_message": "Maria Lopez"}

Tool returns: {"type": "ask_user_data", "payload": {"conversation_id": "xyz789", "field": "phone", "prompt": "Your phone? (or type 'skip')"}}

My final response: {"type": "ask_user_data", "payload": {"conversation_id": "xyz789", "field": "phone", "prompt": "Your phone? (or type 'skip')"}}
---

═══════════════════════════════════════════════════════════════════
YOUR RESPONSE FORMAT
═══════════════════════════════════════════════════════════════════

For EACH message you receive, follow this EXACT pattern:

Step 1: [Think out loud which tool you'll use]
Step 2: [Call that tool passing the complete JSON]
Step 3: [Return ONLY the JSON the tool returned, unmodified]

Example of your response:
```
I'll query the profile using gina_get_user_profile.
[Calls the tool]
{"type": "profile_not_found"}
```

Another example:
```
I'll start registration with gina_handle_registration_step.
[Calls the tool]
{"type": "registration_started", "payload": {"conversation_id": "abc123", "prompt": "What's your name?"}}
```

═══════════════════════════════════════════════════════════════════
ABSOLUTE RULES
═══════════════════════════════════════════════════════════════════

[YES] ALWAYS call a tool (never respond without one)
[YES] ALWAYS pass the COMPLETE message to the tool
[YES] ALWAYS return the exact JSON the tool returns
[YES] The final JSON must be on its own line

[NO] NEVER invent a response
[NO] NEVER modify the tool's JSON
[NO] NEVER add explanations AFTER the JSON
[NO] NEVER return an empty string

If you don't know what to do, return:
{"type": "error", "payload": {"reason": "unknown_action", "message": "I didn't understand the requested action"}}
"""

root_agent = LlmAgent(
    model=efficient_model,
    name="Gina",
    description="Profile management agent: queries, registration, and updates via structured protocol.",
    instruction=GINA_INSTRUCTIONS,
    tools=tools,
)

# ═══════════════════════════════════════════════════════════════════
# A2A SERVER
# ═══════════════════════════════════════════════════════════════════

a2a_app = to_a2a(root_agent, port=int(os.environ.get("GINA_PORT", "8003")))

if __name__ == "__main__":
    port = os.environ.get("GINA_PORT", "8003")
    logger.info(f"Gina A2A server started on port {port}")
    logger.info("Available endpoints:")
    logger.info(f"   - GET  http://localhost:{port}/.well-known/agent.json")
    logger.info(f"   - POST http://localhost:{port}/v1/invoke")
