"""Structured communication protocol between Iris and Alec.
Defines data contracts for inventory queries and loan management.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict


# ═══════════════════════════════════════════════════════════════════
# REQUESTS: Iris → Alec
# ═══════════════════════════════════════════════════════════════════

class CheckAvailabilityRequest(TypedDict):
    """Request to check availability of a book."""
    action: Literal["check_availability"]
    title: str
    author: Optional[str]  # Optional for more precise searches


class GetLoanTermRequest(TypedDict):
    """Request to get the loan term of a book."""
    action: Literal["get_loan_term"]
    title: str


class SearchBooksRequest(TypedDict):
    """Request to search books by criteria."""
    action: Literal["search_books"]
    query: str
    criteria: Optional[Literal["title", "author", "tag"]]  # Default: searches all


# Union type for all possible requests
AlecRequest = CheckAvailabilityRequest | GetLoanTermRequest | SearchBooksRequest


# ═══════════════════════════════════════════════════════════════════
# RESPONSES: Alec → Iris
# ═══════════════════════════════════════════════════════════════════

class BookAvailableResponse(TypedDict):
    """Response when a book is available."""
    type: Literal["book_available"]
    payload: Dict[str, Any]  # {
        # "title": str,
        # "author": str,
        # "available_copies": int,
        # "location": str,
        # "loan_days": int,
        # "conditions": List[str]  # ["Excellent", "Good"]
    # }


class BookNotAvailableResponse(TypedDict):
    """Response when a book is not available (but exists)."""
    type: Literal["book_not_available"]
    payload: Dict[str, Any]  # {
        # "title": str,
        # "author": str,
        # "reason": str,  # "all_borrowed" | "under_repair"
        # "next_return": Optional[str]  # ISO date if known
    # }


class BookNotFoundResponse(TypedDict):
    """Response when a book is not found in the catalog."""
    type: Literal["book_not_found"]
    payload: Dict[str, str]  # {
        # "search_title": str,
        # "message": str,
        # "suggestion": Optional[str]  # Similar titles if exist
    # }


class MultipleResultsResponse(TypedDict):
    """Response when there are multiple matches."""
    type: Literal["multiple_results"]
    payload: Dict[str, Any]  # {
        # "search_title": str,
        # "options": List[Dict[str, str]]  # [{"title": "...", "author": "..."}]
    # }


class LoanTermResponse(TypedDict):
    """Response with loan term information."""
    type: Literal["loan_term"]
    payload: Dict[str, Any]  # {
        # "title": str,
        # "loan_days": int,
        # "applied_rule": str,
        # "return_date": str  # Readable date
    # }


class SearchResultsResponse(TypedDict):
    """Response with search results."""
    type: Literal["search_results"]
    payload: Dict[str, Any]  # {
        # "query": str,
        # "total_results": int,
        # "books": List[Dict[str, Any]]
    # }


class ErrorResponse(TypedDict):
    """Response in case of error."""
    type: Literal["error"]
    payload: Dict[str, str]  # {"reason": "...", "message": "..."}


# Union type for all possible responses
AlecResponse = (
    BookAvailableResponse |
    BookNotAvailableResponse |
    BookNotFoundResponse |
    MultipleResultsResponse |
    LoanTermResponse |
    SearchResultsResponse |
    ErrorResponse
)


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

# Loan rules by material type
LOAN_RULES = {
    "REFERENCE": {
        "days": 7,
        "priority": 1,
        "description": "Frequently consulted reference material"
    },
    "NEW": {
        "days": 14,
        "priority": 2,
        "description": "Recent acquisitions with high demand"
    },
    "NOVEL_EXTENDED": {
        "days": 28,
        "priority": 3,
        "description": "Extended works requiring more reading time"
    },
    "STANDARD": {
        "days": 21,
        "priority": 5,
        "description": "Standard loan for most materials"
    }
}

# Valid states for copies
VALID_STATES = {
    "Available": "Ready for loan",
    "Borrowed": "In hands of a member",
    "Repair": "Requires maintenance",
    "Withdrawn": "Out of circulation"
}

# Umbral de similitud para sugerencias (0-1)
SIMILARITY_THRESHOLD = 0.6
