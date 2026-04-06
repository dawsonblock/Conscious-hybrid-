"""Memory policy rules."""

from hca.common.types import MemoryRecord
from hca.common.enums import MemoryType


def can_write_identity(record: MemoryRecord) -> bool:
    """Determine whether an identity record can be written without approval."""
    # For MVP, require manual approval for identity changes
    return False