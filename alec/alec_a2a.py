"""
Alec A2A - Inventory and logistics management agent.
Handles availability queries, deadline calculations, and searches.
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

from alec_inventory import get_all_books
from alec_utils import (
    calculate_loan_term,
    calculate_return_date,
    check_availability_status,
    format_book_info,
    normalize_text,
    search_in_inventory,
)
from iris_alec_protocol import AlecRequest, AlecResponse

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s [%(levelname)s]: %(message)s'
)
logger = logging.getLogger("alec_a2a")

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

def alec_check_availability(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks the availability of a book in the inventory.
    
    Args:
        args: {
            "action": "check_availability",
            "title": str,
            "author": Optional[str]
        }
    
    Returns:
        {"type": "book_available", "payload": {...}}
        {"type": "book_not_available", "payload": {...}}
        {"type": "book_not_found", "payload": {...}}
        {"type": "multiple_results", "payload": {...}}
        {"type": "error", "payload": {...}}
    """
    try:
        # Parse args if it comes as string
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {args}")
                return {
                    "type": "error",
                    "payload": {
                        "reason": "invalid_json",
                        "message": "The argument must be valid JSON"
                    }
                }
        
        title = args.get("title")
        author = args.get("author")
        
        if not title:
            logger.error("check_availability without title")
            return {
                "type": "error",
                "payload": {
                    "reason": "missing_title",
                    "message": "Book title is required"
                }
            }
        
        logger.info(f"→ CHECK_AVAILABILITY: title='{title}', author='{author}'")
        
        # Search in inventory
        inventory = get_all_books()
        results = search_in_inventory(title, inventory, criteria="title")
        
        # If author was specified, filter by author too
        if author and results:
            results = [
                r for r in results
                if normalize_text(author) in normalize_text(r["data"].get("author", ""))
            ]
        
        # CASE 1: Nothing found
        if not results:
            logger.info(f"← BOOK_NOT_FOUND: '{title}'")
            return {
                "type": "book_not_found",
                "payload": {
                    "search_title": title,
                    "message": f"I couldn't find '{title}' in the catalog",
                    "suggestion": "You can search by author or ask me for similar recommendations"
                }
            }
        
        # CASE 2: Multiple results
        if len(results) > 1:
            options = [
                {
                    "title": r["data"]["title"],
                    "author": r["data"].get("author", "Unknown Author")
                }
                for r in results
            ]
            logger.info(f"← MULTIPLE_RESULTS: {len(results)} matches")
            return {
                "type": "multiple_results",
                "payload": {
                    "search_title": title,
                    "options": options
                }
            }
        
        # CASE 3: Single result - check availability
        book = results[0]["data"]
        copies = book.get("copies", [])
        availability = check_availability_status(copies)
        
        # Calculate loan term
        loan_info = calculate_loan_term(book.get("tags", []))
        
        if availability["available"]:
            logger.info(f"← BOOK_AVAILABLE: '{book['title']}', {availability['quantity']} copies")
            return {
                "type": "book_available",
                "payload": {
                    "title": book["title"],
                    "author": book.get("author", "Unknown Author"),
                    "available_copies": availability["quantity"],
                    "location": book.get("location", "Location not specified"),
                    "loan_days": loan_info["days"],
                    "applied_rule": loan_info["applied_rule"],
                    "return_date": calculate_return_date(loan_info["days"]),
                    "conditions": availability["conditions"]
                }
            }
        else:
            logger.info(f"← BOOK_NOT_AVAILABLE: '{book['title']}', reason={availability['reason']}")
            return {
                "type": "book_not_available",
                "payload": {
                    "title": book["title"],
                    "author": book.get("author", "Unknown Author"),
                    "reason": availability["reason"],
                    "borrowed": availability.get("borrowed", 0),
                    "under_repair": availability.get("under_repair", 0),
                    "message": "All copies are currently borrowed"
                }
            }
    
    except Exception as e:
        logger.exception("Error in alec_check_availability")
        return {
            "type": "error",
            "payload": {
                "reason": "exception",
                "message": str(e)
            }
        }


def alec_search_books(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Searches books by different criteria.
    
    Args:
        args: {
            "action": "search_books",
            "query": str,
            "criteria": Optional["title" | "author" | "tag"]
        }
    
    Returns:
        {"type": "search_results", "payload": {...}}
        {"type": "error", "payload": {...}}
    """
    try:
        # Parse args if it comes as string
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return {
                    "type": "error",
                    "payload": {
                        "reason": "invalid_json",
                        "message": "The argument must be valid JSON"
                    }
                }
        
        query = args.get("query")
        criteria = args.get("criteria")  # Can be None
        
        if not query:
            return {
                "type": "error",
                "payload": {
                    "reason": "missing_query",
                    "message": "A search term is required"
                }
            }
        
        logger.info(f"→ SEARCH_BOOKS: query='{query}', criteria={criteria}")
        
        # Search in inventory
        inventory = get_all_books()
        results = search_in_inventory(query, inventory, criteria)
        
        # Format results
        books = []
        for r in results:
            data = r["data"]
            availability = check_availability_status(data.get("copies", []))
            loan_info = calculate_loan_term(data.get("tags", []))
            
            books.append({
                "title": data["title"],
                "author": data.get("author", "Unknown Author"),
                "available": availability["available"],
                "available_copies": availability["quantity"],
                "location": data.get("location", ""),
                "loan_days": loan_info["days"]
            })
        
        logger.info(f"← SEARCH_RESULTS: {len(books)} results")
        return {
            "type": "search_results",
            "payload": {
                "query": query,
                "criteria": criteria or "all",
                "total_results": len(books),
                "books": books
            }
        }
    
    except Exception as e:
        logger.exception("Error in alec_search_books")
        return {
            "type": "error",
            "payload": {
                "reason": "exception",
                "message": str(e)
            }
        }


# ═══════════════════════════════════════════════════════════════════
# ALEC AGENT
# ═══════════════════════════════════════════════════════════════════

tools = [
    FunctionTool(alec_check_availability),
    FunctionTool(alec_search_books),
]

ALEC_INSTRUCTIONS = """
You are **Alec**, an agent specialized in inventory and logistics management of the library.

IMPORTANT: You MUST ALWAYS call ONE of your tools and return its result.

═══════════════════════════════════════════════════════════════════
YOUR TOOLS
═══════════════════════════════════════════════════════════════════

You have only 2 available tools:

1. alec_check_availability - To verify if a specific book is available
2. alec_search_books - To search books by different criteria

═══════════════════════════════════════════════════════════════════
DECISION: WHICH TOOL TO USE?
═══════════════════════════════════════════════════════════════════

When you receive a message, check the "action" field:

If action is "check_availability":
   → Use alec_check_availability

If action is "search_books":
   → Use alec_search_books

ALWAYS pass the COMPLETE JSON message you received as argument to the tool.

═══════════════════════════════════════════════════════════════════
STEP-BY-STEP EXAMPLES
═══════════════════════════════════════════════════════════════════

EXAMPLE 1: Check availability
---
Message received: {"action": "check_availability", "title": "One Hundred Years of Solitude", "author": "García Márquez"}

Reasoning:
- The action is "check_availability"
- I must use alec_check_availability
- Pass the COMPLETE JSON I received

Action: Call alec_check_availability with {"action": "check_availability", "title": "One Hundred Years of Solitude", "author": "García Márquez"}

Tool returns: {"type": "book_available", "payload": {...}}

My final response: {"type": "book_available", "payload": {...}}
---

EXAMPLE 2: Search books
---
Message received: {"action": "search_books", "query": "García Márquez", "criteria": "author"}

Reasoning:
- The action is "search_books"
- I must use alec_search_books
- Pass the COMPLETE JSON

Action: Call alec_search_books with {"action": "search_books", "query": "García Márquez", "criteria": "author"}

Tool returns: {"type": "search_results", "payload": {"books": [...]}}

My final response: {"type": "search_results", "payload": {"books": [...]}}
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
I'll verify availability with alec_check_availability.
[Calls the tool]
{"type": "book_available", "payload": {"title": "One Hundred Years of Solitude", "available_copies": 3, ...}}
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
    name="Alec",
    description="Inventory management agent: checks availability, calculates loan terms, and searches books.",
    instruction=ALEC_INSTRUCTIONS,
    tools=tools,
)

# ═══════════════════════════════════════════════════════════════════
# A2A SERVER
# ═══════════════════════════════════════════════════════════════════

a2a_app = to_a2a(root_agent, port=int(os.environ.get("ALEC_PORT", "8001")))

if __name__ == "__main__":
    port = os.environ.get("ALEC_PORT", "8001")
    logger.info(f"Alec A2A server started on port {port}")
    logger.info("Available endpoints:")
    logger.info(f"   • GET  http://localhost:{port}/.well-known/agent.json")
    logger.info(f"   • POST http://localhost:{port}/v1/invoke")
