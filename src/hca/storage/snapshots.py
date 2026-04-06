"""Snapshot storage for run state."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from hca.common.time import utc_now

def _path(run_id: str) -> Path:
    return Path(f"storage/runs/{run_id}/snapshots.jsonl")

def append_snapshot(run_id: str, snapshot_data: Dict[str, Any]) -> None:
    """Append a snapshot to the run's snapshots log."""
    path = _path(run_id)
    os.makedirs(path.parent, exist_ok=True)
    
    # Ensure run_id and timestamp are present
    if snapshot_data.get("run_id") in (None, "unknown"):
        snapshot_data["run_id"] = run_id
    if "timestamp" not in snapshot_data:
        snapshot_data["timestamp"] = utc_now().isoformat()
        
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot_data, default=str) + "\n")

def load_latest_snapshot(run_id: str) -> Optional[Dict[str, Any]]:
    """Load the most recent snapshot for a run."""
    path = _path(run_id)
    if not path.exists():
        return None
        
    latest = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                latest = json.loads(line)
            except Exception:
                continue
    return latest
