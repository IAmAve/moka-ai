"""Model recommender — pure business logic, no UI deps."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ModelInfo:
    name: str
    hf_id: str
    size_gb: float
    min_vram_gb: float
    type: str  # base | image | voice


class ModelRecommender:
    """Load tiers.yaml and recommend models based on VRAM tier."""

    def __init__(self, tiers_path: str = None):
        if tiers_path is None:
            tiers_path = Path(__file__).parent.parent / "data" / "tiers.yaml"
        self._tiers_path = Path(tiers_path)
        self._tiers = self._load_tiers()

    def _load_tiers(self) -> dict:
        if not self._tiers_path.exists():
            raise FileNotFoundError(f"tiers.yaml not found at {self._tiers_path}")
        with open(self._tiers_path) as f:
            return yaml.safe_load(f)

    def get_tier(self, vram_gb: float) -> int:
        """Return the tier key (4, 8, 12, 16, 24) for a given VRAM amount."""
        if vram_gb >= 24:
            return 24
        elif vram_gb >= 16:
            return 16
        elif vram_gb >= 12:
            return 12
        elif vram_gb >= 8:
            return 8
        return 4

    def get_recommended_models(self, vram_gb: float) -> dict[str, Optional[ModelInfo]]:
        """Return recommended base/image/voice model for a given VRAM."""
        tier = self.get_tier(vram_gb)
        tier_data = self._tiers.get("tiers", {}).get(tier, {})

        result = {}
        for model_type in ["base", "image", "voice"]:
            m = tier_data.get(model_type)
            if m:
                result[model_type] = ModelInfo(
                    name=m["name"],
                    hf_id=m["hf_id"],
                    size_gb=m["size_gb"],
                    min_vram_gb=m["min_vram_gb"],
                    type=model_type,
                )
            else:
                result[model_type] = None
        return result

    def get_all_models(self) -> list[ModelInfo]:
        """Return all models from tiers.yaml."""
        models = []
        for tier_data in self._tiers.get("tiers", {}).values():
            for model_type, m in tier_data.items():
                models.append(ModelInfo(
                    name=m["name"],
                    hf_id=m["hf_id"],
                    size_gb=m["size_gb"],
                    min_vram_gb=m.get("min_vram_gb", 0),
                    type=model_type,
                ))
        return models

    def check_disk_space(self, install_path: str, models: list[ModelInfo]) -> tuple[bool, float]:
        """Check if there's enough disk space. Returns (sufficient, total_size_gb)."""
        total_gb = sum(m.size_gb for m in models if m)
        try:
            import psutil
            free_gb = psutil.disk_usage(install_path).free / (1024**3)
            return free_gb >= total_gb, total_gb
        except Exception:
            return True, total_gb