"""Hardware scan logic for the installer — pure business logic, no UI."""

from __future__ import annotations

import os
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
    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    all_gpus: list = None   # list of (name, vram_gb)

    def __post_init__(self):
        if self.all_gpus is None:
            self.all_gpus = []


class HardwareScan:
    """Scan hardware: CPU, GPU (all vendors), RAM, VRAM."""

    def scan(self) -> HardwareProfile:
        cpu_info = self._get_cpu_info()
        all_gpus = self._get_all_gpus()
        gpu_model, vram_gb = self._best_gpu(all_gpus)
        compute_cap = self._get_compute_capability(gpu_model)

        mem = psutil.virtual_memory()
        system_ram_gb = round(mem.total / (1024**3), 1)
        available_vram_gb = round(mem.available / (1024**3), 1)

        return HardwareProfile(
            gpu_model=gpu_model,
            vram_gb=vram_gb,
            system_ram_gb=system_ram_gb,
            available_vram_gb=available_vram_gb,
            compute_capability=compute_cap,
            platform=platform.system(),
            cpu_model=cpu_info["name"],
            cpu_cores=cpu_info["cores"],
            cpu_threads=cpu_info["threads"],
            all_gpus=all_gpus,
        )

    # ── CPU ──────────────────────────────────────────────────────────────────

    def _get_cpu_info(self) -> dict:
        """Get human-readable CPU name via WMI (Windows)."""
        if platform.system() == "Windows":
            info = self._wmi_cpu()
            if info:
                return info
        # Fallback for Linux/macOS
        return {
            "name": platform.processor() or "Unknown CPU",
            "cores": psutil.cpu_count(logical=False) or 0,
            "threads": psutil.cpu_count(logical=True) or 0,
        }

    def _wmi_cpu(self) -> Optional[dict]:
        """Get CPU brand name via PowerShell + WMI Win32_Processor."""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WmiObject Win32_Processor | "
                 "Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | "
                 "ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0 or not r.stdout.strip():
                return None
            import json
            data = json.loads(r.stdout)
            # Handle single-object or list
            cpu = data[0] if isinstance(data, list) else data
            name = cpu.get("Name", "").strip()
            if not name:
                return None
            return {
                "name": name,
                "cores": cpu.get("NumberOfCores", 0) or 0,
                "threads": cpu.get("NumberOfLogicalProcessors", 0) or 0,
            }
        except Exception:
            return None

    # ── GPU (all vendors) ────────────────────────────────────────────────────

    def _get_all_gpus(self) -> list:
        """Return list of (name, vram_gb) for ALL GPUs detected."""
        gpus = []

        if platform.system() == "Windows":
            # WMI Win32_VideoController — works for Intel, AMD, NVIDIA
            gpus = self._wmi_all_gpus()
            if gpus:
                return gpus

        # Try nvidia-smi (NVIDIA only)
        nvidia = self._nvidia_smi()
        if nvidia:
            gpus.append((nvidia["name"], nvidia["vram_gb"]))

        # Try PyTorch CUDA fallback
        torch = self._torch_cuda()
        if torch:
            name = torch["name"]
            # Avoid duplicate
            if not any(name.lower() in g[0].lower() for g in gpus):
                gpus.append((name, torch["vram_gb"]))

        return gpus

    def _wmi_all_gpus(self) -> list:
        """Get all GPUs via WMI Win32_VideoController (Intel + AMD + NVIDIA)."""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WmiObject Win32_VideoController | "
                 "Select-Object Name, AdapterRAM | "
                 "ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0 or not r.stdout.strip():
                return []
            import json
            data = json.loads(r.stdout)
            controllers = data if isinstance(data, list) else [data]
            gpus = []
            for ctrl in controllers:
                name = ctrl.get("Name", "").strip()
                if not name or "output" in name.lower() or "null" in name.lower():
                    continue
                vram_bytes = ctrl.get("AdapterRAM") or 0
                vram_gb = round(vram_bytes / (1024**3), 2) if vram_bytes > 0 else 0.0
                gpus.append((name, vram_gb))
            return gpus
        except Exception:
            return []

    def _best_gpu(self, gpus: list) -> tuple:
        """Pick the GPU with highest VRAM (dedicated GPU typically has more)."""
        if not gpus:
            return "No GPU detected", 0.0
        # Sort by VRAM descending — dedicated GPU usually > 2GB
        gpus_sorted = sorted(gpus, key=lambda g: g[1], reverse=True)
        best = gpus_sorted[0]
        return best[0], best[1]

    def _get_compute_capability(self, gpu_name: str) -> Optional[str]:
        """Get CUDA compute capability for NVIDIA GPUs."""
        if not gpu_name:
            return None
        name_lower = gpu_name.lower()
        if "nvidia" not in name_lower and "geforce" not in name_lower and \
           "rtx" not in name_lower and "gtx" not in name_lower:
            return None
        # Try nvidia-smi with compute_cap
        info = self._nvidia_smi()
        if info:
            return info.get("compute_capability")
        return None

    # ── nvidia-smi ────────────────────────────────────────────────────────────

    _NVIDIA_SMI_PATHS = [
        "nvidia-smi",
        "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
        os.path.expandvars("%ProgramFiles%\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe"),
    ]

    def _nvidia_smi(self) -> Optional[dict]:
        """Detect NVIDIA GPU via nvidia-smi at known paths."""
        for smi in self._NVIDIA_SMI_PATHS:
            try:
                r = subprocess.run(
                    [smi,
                     "--query-gpu=name,memory.total,compute_cap",
                     "--format=csv,noheader,nonoheader"],
                    capture_output=True, text=True, timeout=15,
                )
                if r.returncode != 0 or not r.stdout.strip():
                    continue
                parts = [p.strip() for p in r.stdout.strip().split(",")]
                if not parts:
                    continue
                vram_gb = round(float(parts[1]) / 1024, 2)
                return {
                    "name": parts[0],
                    "vram_gb": vram_gb,
                    "compute_capability": parts[2].strip() if len(parts) > 2 and parts[2].strip() else None,
                }
            except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError, OSError):
                continue
        return None

    # ── PyTorch fallback ─────────────────────────────────────────────────────

    def _torch_cuda(self) -> Optional[dict]:
        """PyTorch CUDA fallback."""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "name": torch.cuda.get_device_name(0),
                    "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2),
                }
        except ImportError:
            pass
        return None