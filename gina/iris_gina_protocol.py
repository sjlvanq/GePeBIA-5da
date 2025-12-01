"""
Structured communication protocol between Iris and Gina.
Defines data contracts to ensure consistent communication.
"""

from typing import Any, Dict, Literal, Optional, TypedDict


# ═══════════════════════════════════════════════════════════════════
# REQUESTS: Iris → Gina
# ═══════════════════════════════════════════════════════════════════

class GetProfileRequest(TypedDict):
    """Request to query a user profile."""
    action: Literal["get_profile"]
    user_id: str


class StartRegistrationRequest(TypedDict):
    """Request to start a new registration."""
    action: Literal["start_registration"]


class ContinueRegistrationRequest(TypedDict):
    """Request to continue an ongoing registration."""
    action: Literal["continue_registration"]
    conversation_id: str
    user_message: str


# Union type for all possible requests
GinaRequest = GetProfileRequest | StartRegistrationRequest | ContinueRegistrationRequest


# ═══════════════════════════════════════════════════════════════════
# RESPONSES: Gina → Iris
# ═══════════════════════════════════════════════════════════════════

class ProfileFoundResponse(TypedDict):
    """Response when a profile is found."""
    type: Literal["profile_found"]
    payload: Dict[str, Any]  # {"profile": {...}}


class ProfileNotFoundResponse(TypedDict):
    """Response when a profile is not found."""
    type: Literal["profile_not_found"]


class RegistrationStartedResponse(TypedDict):
    """Response when registration is started."""
    type: Literal["registration_started"]
    payload: Dict[str, str]  # {"conversation_id": "...", "prompt": "..."}


class AskUserDataResponse(TypedDict):
    """Response requesting user data."""
    type: Literal["ask_user_data"]
    payload: Dict[str, str]  # {"conversation_id": "...", "field": "...", "prompt": "..."}


class ConfirmDataResponse(TypedDict):
    """Response requesting data confirmation."""
    type: Literal["confirm_data"]
    payload: Dict[str, str]  # {"conversation_id": "...", "summary": "...", "prompt": "..."}


class RegistrationCompleteResponse(TypedDict):
    """Response when registration is complete."""
    type: Literal["registration_complete"]
    payload: Dict[str, Any]  # {"user_id": "...", "profile": {...}}


class ErrorResponse(TypedDict):
    """Response in case of error."""
    type: Literal["error"]
    payload: Dict[str, str]  # {"reason": "...", "message": "..."}


# Union type for all possible responses
GinaResponse = (
    ProfileFoundResponse |
    ProfileNotFoundResponse |
    RegistrationStartedResponse |
    AskUserDataResponse |
    ConfirmDataResponse |
    RegistrationCompleteResponse |
    ErrorResponse
)


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

# Timeout for registration conversations (30 minutes)
REGISTRATION_TIMEOUT_SECONDS = 1800

# Words considered affirmative
AFFIRMATIVE_WORDS = {
    "yes", "si", "s", "y", "ok", "vale", 
    "correct", "confirm", "clear", "go", "good", "affirmative",
    "yep", "yeah", "simon", "exact", "perfect", "fine"
}

# Words considered negative
NEGATIVE_WORDS = {
    "no", "n", "nope", "negative", "cancel", 
    "cancel", "not now", "later"
}
