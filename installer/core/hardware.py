"""Hardware scan logic for the installer — pure business logic, no UI."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class HardwareProfile:
    gpu_model: str
    vram_gb: float
    system_ram_gb: float
    available_vram_gb: float
    compute_capability: Optional[str] = None
    platform: str = ""


class HardwareScan:
    """Scan hardware: GPU (NVIDIA/AMD/Apple Silicon), RAM, VRAM."""

    def scan(self) -> HardwareProfile:
        gpu_model, vram_gb, compute_capability = self._detect_gpu()
        mem = psutil.virtual_memory()
        system_ram_gb = round(mem.total / (1024**3), 1)
        available_vram_gb = round(mem.available / (1024**3), 1)
        return HardwareProfile(
            gpu_model=gpu_model,
            vram_gb=vram_gb,
            system_ram_gb=system_ram_gb,
            available_vram_gb=available_vram_gb,
            compute_capability=compute_capability,
            platform=platform.system(),
        )

    def _detect_gpu(self):
        """Detect GPU on any platform."""
        info = self._nvidia_smi()
        if info:
            return info["name"], info["vram_gb"], info.get("compute_capability")
        info = self._amd_rocm_smi()
        if info:
            return info["name"], info["vram_gb"], info.get("compute_capability")
        info = self._apple_metal()
        if info:
            return info["name"], info["vram_gb"], None
        info = self._torch_cuda()
        if info:
            return info["name"], info["vram_gb"], None
        cpu = f"{platform.processor() or 'CPU'}"
        return cpu, 0.0, None

    def _nvidia_smi(self) -> Optional[dict]:
        """Detect NVIDIA GPU via nvidia-smi."""
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,compute_arch",
                 "--format=csv,noheader,nonoheader"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode != 0 or not r.stdout.strip():
                return None
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            return {
                "name": parts[0],
                "vram_gb": round(float(parts[1]) / 1024, 2),
                "compute_capability": parts[2] if len(parts) > 2 else None,
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError):
            return None

    def _amd_rocm_smi(self) -> Optional[dict]:
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

    def _apple_metal(self) -> Optional[dict]:
        """Detect Apple Silicon via system_profiler."""
        if platform.system() != "Darwin":
            return None
        try:
            r = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                return None
            import json
            data = json.loads(r.stdout)
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