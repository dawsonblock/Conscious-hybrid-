"""Centralized timestamp generation and parsing."""

from datetime import datetime, timezone
from typing import Optional

def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string."""
    return dt.isoformat()

def parse_iso(value: str) -> datetime:
    """Parse ISO 8601 string to timezone-aware datetime."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
