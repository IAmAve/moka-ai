"""Hardware scan logic for the installer — pure business logic, no UI."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional

import psutil


# Known nvidia-smi locations on Windows (try all of these)
_NVIDIA_SMI_PATHS = [
    "nvidia-smi",  # PATH
    "C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
    "C:\\Program Files (x86)\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
    os.path.expandvars("%ProgramFiles%\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe"),
    os.path.expandvars("%ProgramFiles(x86)%\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe"),
]


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
        """Detect GPU on any platform, try multiple methods in order."""
        # 1. Try nvidia-smi at various paths
        for smi_path in _NVIDIA_SMI_PATHS:
            info = self._nvidia_smi(smi_path)
            if info:
                return info["name"], info["vram_gb"], info.get("compute_capability")

        # 2. Try WMI as fallback (Windows-only, works even if nvidia-smi missing)
        if platform.system() == "Windows":
            info = self._wmi_nvidia()
            if info:
                return info["name"], info["vram_gb"], info.get("compute_capability")

        # 3. Try PyTorch CUDA (works without nvidia-smi)
        info = self._torch_cuda()
        if info:
            return info["name"], info["vram_gb"], None

        # 4. Try AMD ROCm
        info = self._amd_rocm_smi()
        if info:
            return info["name"], info["vram_gb"], info.get("compute_capability")

        # 5. Apple Silicon
        info = self._apple_metal()
        if info:
            return info["name"], info["vram_gb"], None

        cpu = f"{platform.processor() or 'CPU'}"
        return cpu, 0.0, None

    def _nvidia_smi(self, smi_path: str = "nvidia-smi") -> Optional[dict]:
        """Detect NVIDIA GPU via nvidia-smi. Returns None if not found."""
        try:
            # Try --query-gpu with compute_cap (not compute_arch)
            r = subprocess.run(
                [smi_path,
                 "--query-gpu=name,memory.total,compute_cap",
                 "--format=csv,noheader,nonoheader"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0 or not r.stdout.strip():
                return None
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            if not parts:
                return None
            # memory.total is in MiB, convert to GB
            vr_mib = float(parts[1])
            vram_gb = round(vr_mib / 1024, 2)
            return {
                "name": parts[0],
                "vram_gb": vram_gb,
                "compute_capability": parts[2].strip() if len(parts) > 2 and parts[2].strip() else None,
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError, OSError):
            return None

    def _wmi_nvidia(self) -> Optional[dict]:
        """Windows WMI fallback for NVIDIA GPU detection (no nvidia-smi needed)."""
        if platform.system() != "Windows":
            return None
        try:
            import subprocess as _subprocess
            # WMI query for NVIDIA GPU — no nvidia-smi dependency
            r = _subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WmiObject Win32_VideoController | "
                 "Select-Object Name, AdapterRAM | "
                 "ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0 or not r.stdout.strip():
                return None
            import json as _json
            data = _json.loads(r.stdout)
            # Can be a single object or list
            if isinstance(data, list):
                # Pick NVIDIA GPU if present
                for dev in data:
                    name = dev.get("Name", "")
                    if "nvidia" in name.lower() or "geforce" in name.lower() or "rtx" in name.lower() or "gtx" in name.lower():
                        vram_bytes = dev.get("AdapterRAM", 0) or 0
                        vram_gb = round(vram_bytes / (1024**3), 2) if vram_bytes > 0 else 0.0
                        return {"name": name, "vram_gb": vram_gb, "compute_capability": None}
                # No NVIDIA found, return first GPU in list
                dev = data[0]
            else:
                dev = data
            if not dev:
                return None
            name = dev.get("Name", "Unknown GPU")
            vram_bytes = dev.get("AdapterRAM", 0) or 0
            vram_gb = round(vram_bytes / (1024**3), 2) if vram_bytes > 0 else 0.0
            return {"name": name, "vram_gb": vram_gb, "compute_capability": None}
        except Exception:
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