"""HardwareScanner - detect GPU and system hardware for auto-tuned runtime limits."""

from __future__ import annotations

import platform
import subprocess
import sys
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
    """Scans system hardware: GPU (NVIDIA/AMD/Apple Silicon) and system RAM."""

    def scan(self) -> HardwareProfile:
        """Detect GPU and system RAM, return HardwareProfile."""
        system = platform.system()
        gpu_model = "Unknown"
        vram_gb = 0.0
        compute_capability = None

        if system == "Darwin":
            metal_info = self._detect_metal()
            if metal_info:
                gpu_model = metal_info["name"]
                vram_gb = metal_info["vram_gb"]
                compute_capability = metal_info.get("compute_capability")
        else:
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

        # Fallback: torch CUDA as last resort
        if gpu_model == "Unknown":
            torch_info = self._torch_cuda()
            if torch_info:
                gpu_model = torch_info["name"]
                vram_gb = torch_info["vram_gb"]

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
        """Detect AMD GPU via rocm-smi."""
        try:
            r = subprocess.run(
                ["rocm-smi", "--showid", "--showmeminfo", "vram", "--json"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode != 0:
                return None
            import json
            data = json.loads(r.stdout)
            for gpu_id, info in data.items():
                vram_str = info.get("VRAM", {}).get("VRAM Used", "0")
                try:
                    vram_gb = round(float(vram_str.split()[0]) / 1024, 2) if vram_str else 0.0
                except (ValueError, IndexError):
                    vram_gb = 0.0
                return {"name": f"AMD GPU {gpu_id}", "vram_gb": vram_gb, "compute_capability": None}
            return None
        except Exception:
            return None

    def _detect_metal(self) -> Optional[dict]:
        """Detect Apple Silicon GPU via system_profiler."""
        if platform.system() != "Darwin":
            return None
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return None
            import json
            data = json.loads(result.stdout)
            gpus = data.get("SPDisplaysDataType", [])
            if not gpus:
                return None
            gpu = gpus[0]
            vram_str = gpu.get("VRAM", "0")
            vram_gb = 0.0
            try:
                vram_gb = round(float(vram_str.split()[0]) / 1024, 2)
            except (ValueError, IndexError):
                pass
            return {
                "name": gpu.get("chip", "Apple Silicon"),
                "vram_gb": vram_gb,
                "compute_capability": None,
            }
        except Exception:
            return None

    def _torch_cuda(self) -> Optional[dict]:
        """Try PyTorch CUDA as fallback GPU detection."""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "name": torch.cuda.get_device_name(0),
                    "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2),
                    "compute_capability": None,
                }
        except ImportError:
            pass
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