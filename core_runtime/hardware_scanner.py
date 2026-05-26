"""HardwareScanner - detect GPU and system hardware for auto-tuned runtime limits."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class HardwareProfile:
    """Hardware profile detected from the system."""

    gpu_model: str
    vram_gb: float
    system_ram_gb: float
    available_vram_gb: float
    compute_capability: Optional[str] = None


class HardwareScanner:
    """Scans system hardware: GPU (NVIDIA/AMD) and system RAM."""

    def scan(self) -> HardwareProfile:
        """Detect GPU and system RAM, return HardwareProfile."""
        gpu_model = "Unknown"
        vram_gb = 0.0
        compute_capability = None

        # Try NVIDIA first, then AMD
        nvidia_info = self._detect_nvidia()
        if nvidia_info is not None:
            gpu_model = nvidia_info["name"]
            vram_gb = nvidia_info["vram_gb"]
            compute_capability = nvidia_info.get("compute_capability")
        else:
            amd_info = self._detect_amd()
            if amd_info is not None:
                gpu_model = amd_info["name"]
                vram_gb = amd_info["vram_gb"]
                compute_capability = amd_info.get("compute_capability")

        # System RAM (total and available)
        mem = psutil.virtual_memory()
        system_ram_gb = round(mem.total / (1024**3), 2)
        available_vram_gb = round(mem.available / (1024**3), 2)

        return HardwareProfile(
            gpu_model=gpu_model,
            vram_gb=vram_gb,
            system_ram_gb=system_ram_gb,
            available_vram_gb=available_vram_gb,
            compute_capability=compute_capability,
        )

    def _detect_nvidia(self) -> Optional[dict]:
        """Detect NVIDIA GPU via nvidia-smi. Returns dict with name, vram_gb, compute_capability or None."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,compute_arch",
                    "--format=csv,noheader,nonoheader",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            output = result.stdout.strip()
            if not output:
                return None

            parts = [p.strip() for p in output.split(",")]
            if len(parts) < 2:
                return None

            name = parts[0]
            # VRAM in MB, convert to GB
            vram_mb = float(parts[1])
            vram_gb = round(vram_mb / 1024, 2)
            compute_capability = parts[2] if len(parts) > 2 else None

            return {
                "name": name,
                "vram_gb": vram_gb,
                "compute_capability": compute_capability,
            }
        except (subprocess.SubprocessError, FileNotFoundError, ValueError):
            return None

    def _detect_amd(self) -> Optional[dict]:
        """Detect AMD GPU. Placeholder - returns None."""
        # TODO: Implement AMD detection via rocm-smi or Windows APIs
        return None

    def _auto_limits(self, vram_gb: float) -> dict:
        """Return auto-tuned runtime limits based on VRAM tier.

        Args:
            vram_gb: Available VRAM in GB

        Returns:
            dict with max_resolution, max_steps, max_concurrent
        """
        if vram_gb >= 24:
            return {
                "max_resolution": 3072,
                "max_steps": 500,
                "max_concurrent": 4,
            }
        elif vram_gb >= 16:
            return {
                "max_resolution": 2048,
                "max_steps": 200,
                "max_concurrent": 3,
            }
        elif vram_gb >= 8:
            return {
                "max_resolution": 1024,
                "max_steps": 100,
                "max_concurrent": 2,
            }
        else:
            # 4GB or less
            return {
                "max_resolution": 512,
                "max_steps": 50,
                "max_concurrent": 1,
            }