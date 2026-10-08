"""
Remember the farmer's details.

We save the name, village, crops, soil type and land size to a small file. Next
time the app opens, we load it back. We also use these details to give more
personal answers and advice.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import config

PROFILE_PATH = config.ROOT / "farmer_profile.json"   # gitignored

SOIL_TYPES = ["Black cotton (regur)", "Red", "Alluvial", "Laterite",
              "Sandy loam", "Clay", "Loam", "Not sure"]


@dataclass
class Profile:
    name: str = ""
    village: str = ""        # used as weather location too
    district: str = ""
    crops: list = field(default_factory=list)
    soil: str = ""
    land_acres: float = 0.0
    language: str = "auto"   # auto | en | hi | mr

    def is_set(self) -> bool:
        return bool(self.village or self.crops)

    def summary(self) -> str:
        """One-line context string injected into LLM prompts."""
        parts = []
        if self.village or self.district:
            parts.append(f"location: {self.village or ''} {self.district or ''}".strip())
        if self.crops:
            parts.append("crops: " + ", ".join(self.crops))
        if self.soil:
            parts.append("soil: " + self.soil)
        if self.land_acres:
            parts.append(f"land: {self.land_acres} acres")
        return "; ".join(parts)


def load() -> Profile:
    try:
        if PROFILE_PATH.exists():
            return Profile(**json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    return Profile()


def save(p: Profile) -> None:
    PROFILE_PATH.write_text(json.dumps(asdict(p), ensure_ascii=False, indent=2),
                            encoding="utf-8")
