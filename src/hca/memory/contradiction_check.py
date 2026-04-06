"""Logic for detecting contradictions between memory records."""

from typing import List, Dict, Any, Optional, Tuple
from hca.common.types import MemoryRecord

def check_contradictions(new_record: MemoryRecord, existing_records: List[MemoryRecord]) -> List[Tuple[MemoryRecord, str]]:
    """Check for contradictions between a new record and existing memories."""
    contradictions = []
    
    for existing in existing_records:
        # Check for same subject but different content
        if new_record.subject == existing.subject:
            if isinstance(new_record.content, dict) and isinstance(existing.content, dict):
                # If they share the same 'key' but have different 'value'
                if "key" in new_record.content and "key" in existing.content:
                    if new_record.content["key"] == existing.content["key"]:
                        if new_record.content.get("value") != existing.content.get("value"):
                            reason = f"Conflicting value for key '{new_record.content['key']}': '{new_record.content.get('value')}' vs '{existing.content.get('value')}'"
                            contradictions.append((existing, reason))
                else:
                    # Generic dict comparison
                    for key in new_record.content:
                        if key in existing.content and new_record.content[key] != existing.content[key]:
                            reason = f"Conflicting value for key '{key}': '{new_record.content[key]}' vs '{existing.content[key]}'"
                            contradictions.append((existing, reason))
            elif new_record.content != existing.content:
                reason = f"Different content for subject '{new_record.subject}'"
                contradictions.append((existing, reason))
                
    return contradictions

def detect_contradictions(existing_records: List[MemoryRecord], new_record: MemoryRecord) -> bool:
    """Return True if the new record contradicts any existing record."""
    return len(check_contradictions(new_record, existing_records)) > 0
