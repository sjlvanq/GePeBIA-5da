"""
Persistence tools for Gina.
SQLite database handling for user profiles.
"""

import json
import logging
import sqlite3
from typing import Any, Dict

logger = logging.getLogger("gina_tools")

DB_PATH = "gina_users.db"


def _connect():
    """Creates connection and ensures table exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def get_user_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Queries a user profile by ID.
    
    Args:
        args: {"user_id": "<id>"}
        
    Returns:
        {
            "exists": bool,
            "user_id": str,
            "profile": {
                "name": str,
                "phone": str | None,
                "preferences": dict
            } | None
        }
    """
    user_id = args.get("user_id") if isinstance(args, dict) else None
    
    if not user_id:
        logger.warning("get_user_profile called without user_id")
        return {"exists": False, "user_id": None, "profile": None}

    try:
        conn = _connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, name, phone, preferences
            FROM users 
            WHERE user_id = ?
        """, (str(user_id),))
        
        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.info(f"Profile not found: user_id={user_id}")
            return {"exists": False, "user_id": user_id, "profile": None}

        # Parse preferences
        prefs_raw = row[3] or "{}"
        try:
            prefs = json.loads(prefs_raw)
        except json.JSONDecodeError:
            logger.error(f"Malformed preferences for user_id={user_id}")
            prefs = {}

        profile = {
            "name": row[1],
            "phone": row[2],
            "preferences": prefs,
        }
        
        logger.info(f"Profile found: user_id={user_id}, name={row[1]}")
        return {"exists": True, "user_id": row[0], "profile": profile}

    except Exception as e:
        logger.exception(f"Error querying profile: user_id={user_id}")
        return {"exists": False, "user_id": user_id, "profile": None, "error": str(e)}


def save_user_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves or updates a user profile.
    
    Args:
        args: {
            "user_id": "<id>",
            "profile": {
                "name": str,
                "phone": str | None,
                "preferences": dict
            }
        }
        
    Returns:
        {
            "saved": bool,
            "user_id": str,
            "profile": dict
        }
    """
    user_id = args.get("user_id") if isinstance(args, dict) else None
    profile = args.get("profile") if isinstance(args, dict) else None

    if not user_id or not isinstance(profile, dict):
        logger.error(f"save_user_profile with invalid data: user_id={user_id}, profile={profile}")
        return {"saved": False, "reason": "missing_user_id_or_profile"}

    try:
        # Extract fields
        name = profile.get("name")
        phone = profile.get("phone")
        preferences = profile.get("preferences", {})

        if not name:
            logger.error(f"Attempt to save profile without name: user_id={user_id}")
            return {"saved": False, "reason": "missing_name"}

        conn = _connect()
        cursor = conn.cursor()

        # Upsert
        cursor.execute("""
            INSERT INTO users (user_id, name, phone, preferences, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                phone = excluded.phone,
                preferences = excluded.preferences,
                updated_at = CURRENT_TIMESTAMP
        """, (
            str(user_id),
            name,
            phone,
            json.dumps(preferences, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

        logger.info(f"Profile saved successfully: user_id={user_id}, name={name}")
        return {"saved": True, "user_id": user_id, "profile": profile}

    except Exception as e:
        logger.exception(f"Error saving profile: user_id={user_id}")
        return {"saved": False, "reason": "exception", "error": str(e)}


def list_all_users() -> Dict[str, Any]:
    """
    Lists all registered users (useful for debugging).
    
    Returns:
        {
            "count": int,
            "users": [{"user_id": str, "name": str}, ...]
        }
    """
    try:
        conn = _connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, name FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        users = [{"user_id": row[0], "name": row[1]} for row in rows]
        
        return {"count": len(users), "users": users}
        
    except Exception as e:
        logger.exception("Error listing users")
        return {"count": 0, "users": [], "error": str(e)}
