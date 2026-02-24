from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class AuditEvent:
    event_id: str
    timestamp: str
    redacted_input: str
    route: Dict[str, Any]
    plan: Dict[str, Any]
    redaction_counts: Dict[str, int]
    sql: Optional[Dict[str, Any]] = None  # ✅ NEW


def write_audit_event(event: AuditEvent, audit_dir: str = "audit") -> str:
    os.makedirs(audit_dir, exist_ok=True)
    path = os.path.join(audit_dir, f"{event.event_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(event), f, indent=2, ensure_ascii=False)
    return path