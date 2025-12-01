"""
Utilities for validation and data handling in Gina.
"""

import logging
import random
import re
import string
import time
from typing import Any, Dict, Optional

from iris_gina_protocol import AFFIRMATIVE_WORDS, REGISTRATION_TIMEOUT_SECONDS

logger = logging.getLogger("gina_utils")


# ═══════════════════════════════════════════════════════════════════
# ID GENERATION
# ═══════════════════════════════════════════════════════════════════

USED_USER_IDS = set()  # To avoid ID collisions


def generate_user_id() -> str:
    """Generates a unique 5-digit user_id."""
    for _ in range(1000):
        candidate = "".join(random.choices(string.digits, k=5))
        if candidate not in USED_USER_IDS:
            USED_USER_IDS.add(candidate)
            return candidate
    
    # Fallback (very rare) - use timestamp
    return str(int(time.time()))[-5:]


def generate_conversation_id() -> str:
    """Generates a unique alphanumeric conversation_id."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=12))


# ═══════════════════════════════════════════════════════════════════
# DATA VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_name(text: str) -> Optional[str]:
    """
    Validates that the text looks like a valid name.
    
    Requirements:
    - Minimum 2 characters
    - At least 50% letters
    - Not just numbers
    - No problematic special characters
    
    Args:
        text: Text to validate
        
    Returns:
        Clean name if valid, None if not
    """
    if not text:
        return None
    
    cleaned = text.strip()
    
    # Too short
    if len(cleaned) < 2:
        return None
    
    # Only numbers
    if cleaned.isdigit():
        return None
    
    # Must have a reasonable proportion of letters
    letter_count = sum(1 for ch in cleaned if ch.isalpha())
    if letter_count < len(cleaned) * 0.5:
        return None
    
    # Should not have problematic special characters
    # Allow: letters, spaces, hyphens, apostrophes, accents
    if re.search(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-\']', cleaned):
        return None
    
    return cleaned


def validate_phone(text: str) -> Optional[str]:
    """
    Validates and extracts a phone number.
    
    Accepts formats like:
    - 3815551234
    - 381-555-1234
    - (381) 555-1234
    - +54 381 555 1234
    
    Args:
        text: Text containing the phone number
        
    Returns:
        Only the digits if valid (minimum 6), None if not
    """
    if not text:
        return None
    
    # Extract only digits
    digits = "".join(ch for ch in text if ch.isdigit())
    
    # Minimum 6 digits (short local phones)
    # Maximum 15 digits (E.164 standard)
    if 6 <= len(digits) <= 15:
        return digits
    
    return None


def is_affirmative(text: str) -> bool:
    """
    Detects if the text is an affirmation.
    
    Args:
        text: User text
        
    Returns:
        True if affirmative, False if not
    """
    if not text:
        return False
    
    # Clean the text: remove punctuation and normalize
    import re
    cleaned = re.sub(r'[^\w\s]', '', text.strip().lower())
    
    # Normalize accents
    normalized = cleaned.replace('i', 'i')
    
    # Check against affirmative words
    result = normalized in AFFIRMATIVE_WORDS or cleaned in AFFIRMATIVE_WORDS
    
    logger.debug(f"is_affirmative('{text}') -> cleaned='{cleaned}', normalized='{normalized}', result={result}")
    
    return result


def is_skip_request(text: str) -> bool:
    """
    Detects if the user wants to skip a field.
    
    Args:
        text: User text
        
    Returns:
        True if wants to skip, False if not
    """
    if not text:
        return False
    
    skip_words = {"skip", "no", "none", "nothing", "prefer not"}
    normalized = text.strip().lower()
    
    return normalized in skip_words or any(word in normalized for word in skip_words)


# ═══════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

REGISTRATIONS: Dict[str, Dict[str, Any]] = {}


def create_registration_state(conversation_id: str) -> Dict[str, Any]:
    """
    Creates a new registration state.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Initial state
    """
    now = time.time()
    state = {
        "stage": "started",
        "collected": {},
        "created_at": now,
        "last_activity": now
    }
    REGISTRATIONS[conversation_id] = state
    return state


def get_registration_state(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Gets the state of a registration.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        State if exists, None if not
    """
    return REGISTRATIONS.get(conversation_id)


def update_registration_activity(conversation_id: str) -> None:
    """
    Updates the timestamp of last activity.
    
    Args:
        conversation_id: Conversation ID
    """
    if conversation_id in REGISTRATIONS:
        REGISTRATIONS[conversation_id]["last_activity"] = time.time()


def cleanup_stale_registrations() -> int:
    """
    Removes abandoned registrations.
    
    Returns:
        Number of registrations removed
    """
    now = time.time()
    stale_ids = [
        conv_id for conv_id, state in REGISTRATIONS.items()
        if now - state["last_activity"] > REGISTRATION_TIMEOUT_SECONDS
    ]
    
    for conv_id in stale_ids:
        REGISTRATIONS.pop(conv_id)
        logger.info(f"Abandoned registration removed: {conv_id}")
    
    return len(stale_ids)


def delete_registration(conversation_id: str) -> None:
    """
    Deletes a specific registration.
    
    Args:
        conversation_id: Conversation ID
    """
    REGISTRATIONS.pop(conversation_id, None)


# ═══════════════════════════════════════════════════════════════════
# DATA FORMATTING
# ═══════════════════════════════════════════════════════════════════

def create_empty_profile_preferences() -> Dict[str, Any]:
    """
    Creates the empty preferences structure for a new profile.
    
    Returns:
        Dict with preferences structure
    """
    return {
        "favorite_genres": [],
        "favorite_authors": [],
        "reading_themes": [],
        "recent_interests": [],
        "reader_profile": {
            "experience_level": None,
            "reading_speed": None,
            "comfort_topics": []
        },
        "borrowing_habits": {
            "average_loan_duration": None,
            "frequency": None,
            "typical_format": None
        },
        "accessibility": {
            "needs_large_print": False,
            "prefers_audiobooks": False,
            "language_preference": "en"
        }
    }


def create_profile_from_collected_data(collected: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a complete profile from collected data.
    
    Args:
        collected: Data collected during registration
        
    Returns:
        Complete profile with expected structure
    """
    return {
        "name": collected.get("name"),
        "phone": collected.get("phone"),
        "preferences": create_empty_profile_preferences()
    }
