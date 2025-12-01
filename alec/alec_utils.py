"""
"""Utilities for search, validation, and calculations in Alec.
"""

import datetime
import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from iris_alec_protocol import LOAN_RULES

logger = logging.getLogger("alec_utils")


# ═══════════════════════════════════════════════════════════════════
# TEXT NORMALIZATION
# ═══════════════════════════════════════════════════════════════════

def normalize_text(text: str) -> str:
    """
    Normalizes text for searches (lowercase, no accents, no extra punctuation).
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # To lowercase
    normalized = text.lower().strip()
    
    # Remove accents
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n'
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized


# ═══════════════════════════════════════════════════════════════════
# SEARCH AND MATCHING
# ═══════════════════════════════════════════════════════════════════

def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculates similarity between two strings (0.0 to 1.0).
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score (1.0 = identical)
    """
    return SequenceMatcher(None, normalize_text(str1), normalize_text(str2)).ratio()


def find_best_match(query: str, options: List[str], threshold: float = 0.6) -> Optional[Tuple[str, float]]:
    """
    Finds the best match in a list of options.
    
    Args:
        query: Text to search
        options: List of available options
        threshold: Minimum similarity threshold
        
    Returns:
        Tuple (best_option, score) or None if none exceeds threshold
    """
    if not options:
        return None
    
    query_norm = normalize_text(query)
    best_match = None
    best_score = 0.0
    
    for option in options:
        score = calculate_similarity(query_norm, option)
        if score > best_score:
            best_score = score
            best_match = option
    
    if best_score >= threshold:
        return (best_match, best_score)
    
    return None


def search_in_inventory(
    query: str,
    inventory: Dict[str, Any],
    criteria: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Searches inventory by different criteria.
    
    Args:
        query: Search text
        inventory: Inventory dictionary
        criteria: "title", "author", "tag" or None (searches all)
        
    Returns:
        List of books that match
    """
    query_norm = normalize_text(query)
    results = []
    
    for key, data in inventory.items():
        match = False
        
        # Search in title
        if criteria in [None, "title"]:
            if query_norm in normalize_text(data["title"]) or query_norm in key:
                match = True
        
        # Search in author
        if criteria in [None, "author"]:
            if query_norm in normalize_text(data.get("author", "")):
                match = True
        
        # Search in tags
        if criteria in [None, "tag"]:
            tags_normalized = [normalize_text(tag) for tag in data.get("tags", [])]
            if any(query_norm in tag for tag in tags_normalized):
                match = True
        
        if match:
            results.append({
                "key": key,
                "data": data
            })
    
    return results


# ═══════════════════════════════════════════════════════════════════
# AVAILABILITY CALCULATION
# ═══════════════════════════════════════════════════════════════════

def count_available_copies(copies: List[Dict[str, str]]) -> int:
    """
    Counts how many copies are available.
    
    Args:
        copies: List of copies from the book
        
    Returns:
        Number of available copies
    """
    return sum(1 for copy in copies if copy.get("status") == "Available")


def get_copy_conditions(copies: List[Dict[str, str]]) -> List[str]:
    """
    Gets list of conditions of available copies.
    
    Args:
        copies: List of copies from the book
        
    Returns:
        List of conditions (["Excellent", "Good"])
    """
    conditions = []
    for copy in copies:
        if copy.get("status") == "Available":
            conditions.append(copy.get("condition", "Unknown"))
    return conditions


def check_availability_status(copies: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Analyzes the availability status of a book.
    
    Args:
        copies: List of copies from the book
        
    Returns:
        Dict with:
        - available: bool
        - quantity: int
        - reason: str (if not available)
        - conditions: List[str]
    """
    total = len(copies)
    available = count_available_copies(copies)
    borrowed = sum(1 for copy in copies if copy.get("status") == "Borrowed")
    under_repair = sum(1 for copy in copies if copy.get("status") == "Repair")
    
    if available > 0:
        return {
            "available": True,
            "quantity": available,
            "conditions": get_copy_conditions(copies)
        }
    
    # Not available - determine reason
    if borrowed == total:
        reason = "all_borrowed"
    elif under_repair > 0:
        reason = "under_repair"
    else:
        reason = "not_available"
    
    return {
        "available": False,
        "quantity": 0,
        "reason": reason,
        "borrowed": borrowed,
        "under_repair": under_repair
    }


# ═══════════════════════════════════════════════════════════════════
# LOAN TERM CALCULATION
# ═══════════════════════════════════════════════════════════════════

def calculate_loan_term(tags: List[str]) -> Dict[str, Any]:
    """
    Calculates the loan term based on tags and priority.
    
    Priority: lower number = higher priority
    In case of tie, the longest term is favored for the user.
    
    Args:
        tags: List of book tags
        
    Returns:
        Dict with days, applied_rule, priority
    """
    # Default rule
    winning_rule = LOAN_RULES["STANDARD"]
    applied_tag = "STANDARD"
    
    for tag in tags:
        tag_norm = normalize_text(tag).replace(" ", "_").upper()
        
        # Look for exact rule
        if tag_norm in LOAN_RULES:
            current_rule = LOAN_RULES[tag_norm]
            
            # Apply by priority
            if current_rule["priority"] < winning_rule["priority"]:
                winning_rule = current_rule
                applied_tag = tag_norm
            
            # Tie-breaker: more days favors user
            elif current_rule["priority"] == winning_rule["priority"]:
                if current_rule["days"] > winning_rule["days"]:
                    winning_rule = current_rule
                    applied_tag = tag_norm
    
    return {
        "days": winning_rule["days"],
        "applied_rule": applied_tag,
        "priority": winning_rule["priority"],
        "description": winning_rule["description"]
    }


def calculate_return_date(days: int) -> str:
    """
    Calculates return date from today.
    
    Args:
        days: Number of loan days
        
    Returns:
        Readable date in Spanish format (e.g.: "December 23, 2024")
    """
    date = datetime.date.today() + datetime.timedelta(days=days)
    
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    return f"{date.day} of {months[date.month - 1]} of {date.year}"


# ═══════════════════════════════════════════════════════════════════
# RESPONSE FORMATTING
# ═══════════════════════════════════════════════════════════════════

def format_book_info(data: Dict[str, Any], include_availability: bool = True) -> Dict[str, Any]:
    """
    Formats book information for responses.
    
    Args:
        data: Book data from inventory
        include_availability: Whether to include availability info
        
    Returns:
        Dict formatted for response
    """
    info = {
        "title": data.get("title", ""),
        "author": data.get("author", ""),
        "location": data.get("location", "")
    }
    
    if include_availability:
        copies = data.get("copies", [])
        availability = check_availability_status(copies)
        info.update(availability)
    
    return info
