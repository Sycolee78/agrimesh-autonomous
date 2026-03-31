"""Simple local storage for farm profiles.

Stores profiles in a JSON file on disk (no auth / multi-user separation yet).

This is intentionally simple for the simulation MVP; can be replaced later
with a proper database + user accounts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


STORAGE_PATH = Path(__file__).parent.parent.parent / "data" / "farm_profiles.json"
STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class StoredFarmProfile:
    profile_id: str
    name: str
    description: str
    farm_config: Dict
    created_at: str
    updated_at: str


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _load_all() -> Dict[str, StoredFarmProfile]:
    if not STORAGE_PATH.exists():
        return {}
    try:
        raw = json.loads(STORAGE_PATH.read_text())
    except Exception:
        return {}

    profiles: Dict[str, StoredFarmProfile] = {}
    for pid, data in raw.items():
        try:
            profiles[pid] = StoredFarmProfile(
                profile_id=pid,
                name=data.get("name", "Unnamed farm"),
                description=data.get("description", ""),
                farm_config=data.get("farm_config", {}),
                created_at=data.get("created_at", _now_iso()),
                updated_at=data.get("updated_at", _now_iso()),
            )
        except Exception:
            continue
    return profiles


def _save_all(profiles: Dict[str, StoredFarmProfile]) -> None:
    serializable = {
        pid: {
            "name": p.name,
            "description": p.description,
            "farm_config": p.farm_config,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for pid, p in profiles.items()
    }
    STORAGE_PATH.write_text(json.dumps(serializable, indent=2, sort_keys=True))


def list_profiles() -> List[StoredFarmProfile]:
    return list(_load_all().values())


def get_profile(profile_id: str) -> Optional[StoredFarmProfile]:
    return _load_all().get(profile_id)


def create_profile(name: str, description: str, farm_config: Dict) -> StoredFarmProfile:
    profiles = _load_all()
    profile_id = f"farm-{int(datetime.utcnow().timestamp())}"
    now = _now_iso()
    profile = StoredFarmProfile(
        profile_id=profile_id,
        name=name or "My Farm",
        description=description or "",
        farm_config=farm_config,
        created_at=now,
        updated_at=now,
    )
    profiles[profile_id] = profile
    _save_all(profiles)
    return profile


def update_profile(profile_id: str, name: Optional[str], description: Optional[str], farm_config: Optional[Dict]) -> Optional[StoredFarmProfile]:
    profiles = _load_all()
    existing = profiles.get(profile_id)
    if not existing:
        return None
    if name is not None:
        existing.name = name
    if description is not None:
        existing.description = description
    if farm_config is not None:
        existing.farm_config = farm_config
    existing.updated_at = _now_iso()
    profiles[profile_id] = existing
    _save_all(profiles)
    return existing


def delete_profile(profile_id: str) -> bool:
    profiles = _load_all()
    if profile_id not in profiles:
        return False
    del profiles[profile_id]
    _save_all(profiles)
    return True
