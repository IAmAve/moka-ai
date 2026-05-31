"""Model recommender — pure business logic, no UI deps."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ModelInfo:
    name: str
    github_asset: Optional[str]  # filename in GitHub release (e.g. "llama3.2-1b-q4_k_m.gguf")
    github_tag: str               # release tag (e.g. "v1.0" or "latest")
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
        with open(self._tiers_path, encoding="utf-8") as f:
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
                    github_asset=m.get("github_asset", ""),
                    github_tag=m.get("github_tag", "latest"),
                    size_gb=m["size_gb"],
                    min_vram_gb=m.get("min_vram_gb", 0),
                    type=model_type,
                )
            else:
                result[model_type] = None
        return result

    def get_all_models(self) -> list[ModelInfo]:
        """Return all unique models from tiers.yaml, deduplicated by name."""
        seen = set()
        models = []
        for tier_data in self._tiers.get("tiers", {}).values():
            for model_type, m in tier_data.items():
                if m["name"] not in seen:
                    seen.add(m["name"])
                    models.append(ModelInfo(
                        name=m["name"],
                        github_asset=m.get("github_asset", ""),
                        github_tag=m.get("github_tag", "latest"),
                        size_gb=m.get("size_gb", 0),
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


# ── Ollama model catalog ───────────────────────────────────────────────────

@dataclass
class OllamaModel:
    """A single model from the Ollama library."""
    name: str           # e.g. "deepseek-coder:7b"
    display_name: str   # e.g. "DeepSeek Coder 7B"
    size_gb: float
    min_ram_gb: float
    quantization: str    # e.g. "Q4_K_M", "Q5_K_M"
    description: str
    last_updated: str

    @property
    def short_name(self) -> str:
        """Short identifier safe for display and API calls."""
        return self.name

    def is_compatible(self, vram_gb: float, system_ram_gb: float) -> bool:
        """Check if this model fits in available VRAM + RAM."""
        usable_ram = vram_gb + (system_ram_gb * 0.5)
        return self.size_gb <= usable_ram


class OllamaCatalog:
    """Search and manage models from the Ollama library during installation.

    Uses `ollama search` to query models (requires internet at install time only).
    No background service needed — Ollama pulls models into ~/.ollama/models/
    at install time, and Moka uses llama.cpp to load them directly at runtime.
    """

    def __init__(
        self,
        vram_gb: float = 8.0,
        system_ram_gb: float = 16.0,
        logger: callable = None,
    ):
        self.vram = vram_gb
        self.ram = system_ram_gb
        self._log = logger or (lambda m: None)
        self._ollama_path = self._find_ollama()
        # Known size estimates for popular models (name_prefix → size_gb, min_ram_gb)
        self._known_models: dict[str, tuple[float, float]] = {
            "codellama":          (4.2,  6),
            "deepseek-coder":     (4.1,  6),
            "deepseek-coder:1.3": (1.4,  3),
            "deepseek-coder:2.5": (2.6,  4),
            "deepseek-coder:6":   (3.6,  5),
            "deepseek-coder:7":   (4.1,  6),
            "deepseek-coder:8":   (4.7,  7),
            "deepseek-coder:14": (8.1,  12),
            "deepseek-coder:33": (18.0, 20),
            "llama3.1":          (4.3,  6),
            "llama3.1:8":        (4.7,  7),
            "llama3.2":          (2.0,  4),
            "llama3.2:3":        (2.0,  4),
            "llama3.2:1":        (1.3,  3),
            "mistral":           (4.1,  6),
            "mistral-nemo":      (7.1,  8),
            "qwen2.5":           (5.8,  8),
            "qwen2.5-coder":     (5.8,  8),
            "qwen2.5-coder:3":   (2.0,  4),
            "qwen2.5-coder:1.5": (1.3,  3),
            "phi3":              (2.2,  4),
            "phi3:3.8":          (2.2,  4),
            "phi3:14":           (7.9,  10),
            "gemma2":            (5.2,  7),
            "gemma2:2b":         (1.6,  3),
            "gemma2:9b":         (5.2,  7),
            "codegemma":         (5.2,  7),
            "nomicomo":          (1.4,  3),
            "starcoder2":        (3.0,  5),
            "starcoder2:3":      (1.0,  2),
            "starcoder2:7":      (3.8,  5),
            "llava":             (4.3,  6),
            "llava:7b":          (4.3,  6),
            "llava:13b":         (7.3,  9),
            "bakllava":          (4.3,  6),
            "moondream":         (1.4,  3),
            "llama3:70b":        (39.0, 32),
            "mixtral":           (26.0, 16),
            "mistral-large":     (26.0, 16),
        }

    # ── ollama detection ───────────────────────────────────────────────

    def _find_ollama(self) -> Optional[str]:
        """Find ollama binary. Returns path or None."""
        path = shutil.which("ollama")
        if not path:
            for candidate in [
                os.path.expandvars(r"%LOCALAPPDATA%\Ollama\ollama.exe"),
                r"C:\Ollama\ollama.exe",
                "/usr/local/bin/ollama",
                "/opt/homebrew/bin/ollama",
            ]:
                if os.path.isfile(candidate):
                    path = candidate
                    break
        return path

    def ensure_ollama(self) -> bool:
        """Install Ollama if not found. Returns True on success."""
        if self._ollama_path:
            return True
        self._log("[OllamaCatalog] Ollama not found — installing...")
        return self._install_ollama()

    def _install_ollama(self) -> bool:
        """Install Ollama via the official installer script."""
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "irm https://ollama.com/install.ps1 | iex"],
                    capture_output=True, text=True, timeout=180,
                )
            else:
                result = subprocess.run(
                    ["curl", "-fsSL", "https://ollama.com/install.sh"],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 0:
                    # On linux/mac the install script outputs bash — run it
                    p = subprocess.run(result.stdout, shell=True, capture_output=True, timeout=120)
                    result = p
            if result.returncode == 0:
                self._ollama_path = shutil.which("ollama")
                self._log("[OllamaCatalog] Ollama installed")
                return True
            self._log(f"[OllamaCatalog] Ollama install failed: {result.stderr[:200]}")
            return False
        except Exception as e:
            self._log(f"[OllamaCatalog] Ollama install error: {e}")
            return False

    # ── search ───────────────────────────────────────────────────────────

    def search(self, query: str = "") -> list[OllamaModel]:
        """Search Ollama library for models matching query (internet needed).

        Returns list of OllamaModel sorted by compatibility (best fit first).
        Falls back to local-only if offline.
        """
        if not self.ensure_ollama():
            return self._local_models()

        self._log(f"[OllamaCatalog] Searching: {query!r}")
        try:
            # Try `ollama search` CLI — official way to search remote library
            cmd = ["ollama", "search", query] if query else ["ollama", "search", "coder"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0 and result.stdout.strip():
                models = self._parse_ollama_search(result.stdout)
                # Sort: compatible models first, then by size
                compatible = [m for m in models if m.is_compatible(self.vram, self.ram)]
                incompatible = [m for m in models if not m.is_compatible(self.vram, self.ram)]
                # Also include known models not in search results
                known = self._known_by_query(query)
                for km in known:
                    if not any(km.name == m.name for m in (compatible + incompatible)):
                        (compatible if km.is_compatible(self.vram, self.ram) else incompatible).append(km)
                return compatible + incompatible
        except Exception as e:
            self._log(f"[OllamaCatalog] search error: {e}")

        return self._local_models() + self._known_by_query(query)

    def _parse_ollama_search(self, raw: str) -> list[OllamaModel]:
        """Parse output of `ollama search <query>` CLI command.

        Output format (multi-line, varies by Ollama version):
          NAME                    DIMENSIONS  SIZE      MODIFIED
          deepseek-coder:7b       3584        4.1GB     2025-01-23
          deepseek-coder:3b       2048        1.6GB     2025-01-20
        """
        models = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("NAME ") or "DIMENSIONS" in line:
                continue
            parts = re.split(r"\s{2,}", line)
            if len(parts) >= 3:
                name = parts[0].strip()
                size_raw = parts[2].strip() if len(parts) > 2 else ""
                size_gb = self._parse_size(size_raw)
                min_ram = max(size_gb * 0.8, 2.0)
                description = ""
                if len(parts) > 3:
                    description = parts[3].strip()
                display_name = name.replace(":", " ").replace("-", " ").replace("_", " ")
                quant = self._infer_quantization(name)
                models.append(OllamaModel(
                    name=name,
                    display_name=display_name,
                    size_gb=size_gb,
                    min_ram_gb=min_ram,
                    quantization=quant,
                    description=description,
                    last_updated="",
                ))
        return models

    def _parse_size(self, size_raw: str) -> float:
        """Convert size string like '4.1GB' or '1.2GB' to float GB."""
        size_raw = size_raw.upper().strip()
        m = re.match(r"([\d.]+)\s*GB|MB|TB", size_raw)
        if m:
            val = float(m.group(1))
            unit = re.search(r"MB|MB|TB", size_raw)
            if unit and "MB" in unit.group(0):
                val /= 1024
            elif "TB" in unit.group(0) if unit else False:
                val *= 1024
            return round(val, 1)
        return 5.0  # safe default

    def _infer_quantization(self, model_name: str) -> str:
        """Infer a good quantization level from model name or return Q4_K_M default."""
        name_lower = model_name.lower()
        if "30b" in name_lower or "33b" in name_lower or "34b" in name_lower:
            return "Q4_K_M"
        if "70b" in name_lower or "65b" in name_lower:
            return "Q4_K_M"
        if "7b" in name_lower or "8b" in name_lower:
            return "Q4_K_M"
        if "3b" in name_lower:
            return "Q4_K_M"
        if "1b" in name_lower or "1.5b" in name_lower:
            return "Q4_K_M"
        return "Q4_K_M"

    def _known_by_query(self, query: str) -> list[OllamaModel]:
        """Return known models that match query string."""
        query_lower = query.lower()
        results = []
        # Keywords that indicate the user wants a code model
        code_keywords = ["code", "coder", "programming", "dev"]
        is_coding_query = any(k in query_lower for k in code_keywords)

        for name_prefix, (size_gb, min_ram) in self._known_models.items():
            q = query_lower.strip()
            # Empty query = show code models + general purpose
            if not q or q in name_prefix.lower() or any(k in name_prefix.lower() for k in q.split()):
                if not is_coding_query or "code" in name_prefix or q in name_prefix:
                    display = name_prefix.replace("-", " ").replace("_", " ")
                    # Build full ollama name: "deepseek-coder:7b"
                    if ":" not in name_prefix:
                        full_name = f"{name_prefix}:latest"
                        # Try to give a specific size hint
                        for size_suffix in ["1.3b", "3b", "7b", "8b", "14b", "33b"]:
                            if size_suffix.replace(".", "") in name_prefix.replace("-", "").replace("_", ""):
                                full_name = f"{name_prefix}:{size_suffix}"
                                break
                    else:
                        full_name = name_prefix

                    # Check we haven't already returned this
                    results.append(OllamaModel(
                        name=full_name,
                        display_name=display,
                        size_gb=size_gb,
                        min_ram_gb=min_ram,
                        quantization="Q4_K_M",
                        description="Ollama library model" + (" — coding specialized" if "code" in name_prefix else ""),
                        last_updated="",
                    ))
        return sorted(results, key=lambda m: m.size_gb)

    def _local_models(self) -> list[OllamaModel]:
        """Return models already downloaded to this machine."""
        if not self._ollama_path:
            return []
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
            )
            if result.returncode != 0:
                return []
            models = []
            for line in result.stdout.splitlines()[1:]:  # skip header
                line = line.strip()
                if not line:
                    continue
                parts = re.split(r"\s{2,}", line)
                if parts:
                    name = parts[0].strip()
                    size_gb = self._parse_size(parts[1].strip()) if len(parts) > 1 else 5.0
                    models.append(OllamaModel(
                        name=name, display_name=name,
                        size_gb=size_gb, min_ram_gb=max(size_gb * 0.8, 2.0),
                        quantization="Q4_K_M", description="locally available", last_updated="",
                    ))
            return models
        except Exception:
            return []

    def pull(
        self,
        model_name: str,
        progress_callback: callable = None,
        total_weight: float = 0.25,
        start_pct: float = 0.0,
    ) -> bool:
        """Pull a model from Ollama library via `ollama pull` (internet required).

        Streams progress to progress_callback(msg, pct).
        Returns True on success, False on failure.
        """
        if not self.ensure_ollama():
            return False

        def _log(msg):
            if self._log:
                self._log(msg)

        _log(f"[OllamaCatalog] Pulling {model_name}...")
        if progress_callback:
            progress_callback(f"Downloading {model_name}...", start_pct)

        try:
            proc = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
            last_msg = ""
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if not line or line == last_msg:
                    continue
                last_msg = line
                _log(f"  {line}")
                if progress_callback:
                    # Parse: "downloading 2.1GB / 4.1GB  — 51%"
                    pct = self._parse_pull_progress(line, total_weight, start_pct)
                    progress_callback(line, pct)
            proc.wait()
            if proc.returncode == 0:
                _log(f"[OllamaCatalog] Pull complete: {model_name}")
                if progress_callback:
                    progress_callback(f"OK — {model_name} ready", start_pct + total_weight)
                return True
            _log(f"[OllamaCatalog] Pull failed (exit {proc.returncode})")
            return False
        except Exception as e:
            _log(f"[OllamaCatalog] Pull error: {e}")
            return False

    def _parse_pull_progress(self, line: str, total_weight: float, start_pct: float) -> float:
        """Parse `ollama pull` output line to a 0-1 progress fraction."""
        # e.g. "downloading 2.1GB / 4.1GB  — 51%" or "verifying sha256..."
        m = re.search(r"(\d+)%\s*$", line)
        if m:
            pct = int(m.group(1)) / 100.0
            return start_pct + pct * total_weight
        # Still downloading but no percentage
        if "downloading" in line.lower():
            return start_pct + total_weight * 0.5
        if "success" in line.lower():
            return start_pct + total_weight
        return start_pct

    def model_path(self, model_name: str) -> Optional[str]:
        """Return the path to a locally-pulled model's files."""
        if not self._ollama_path:
            return None
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
            )
            if result.returncode == 0 and model_name in result.stdout:
                # Model is present locally
                return f"~/.ollama/models/blobs/"  # blob storage, not directly usable as GGUF
        except Exception:
            pass
        return None


# ── HuggingFace GGUF model catalog ─────────────────────────────────────────

class HuggingFaceCatalog:
    """Search and download GGUF models from HuggingFace at install time.

    Uses the HuggingFace Hub REST API to find GGUF-format models,
    then downloads the selected .gguf file using huggingface_hub.
    Moka runs the GGUF at runtime via llama-cpp-python
    (pip-installable, no Ollama required).

    Internet required during installation only.
    """

    def __init__(
        self,
        vram_gb: float = 8.0,
        system_ram_gb: float = 16.0,
        logger: callable = None,
    ):
        self.vram = vram_gb
        self.ram  = system_ram_gb
        self._log = logger or (lambda m: None)

    def search(self, query: str = "") -> list[OllamaModel]:
        """Search HuggingFace for GGUF models matching query.

        Returns list of OllamaModel (same dataclass used by OllamaCatalog)
        sorted by compatibility, then by downloads.
        """
        from installer.core.downloader import HuggingFaceDownloader

        dl = HuggingFaceDownloader(models_dir="", progress_callback=lambda m, p: None)
        raw = dl.search_models(query=query, vram_gb=self.vram, limit=30)

        models = []
        for r in raw:
            best = r.get("best_file", "")
            if "." in best:
                stem = best.rsplit(".", 1)
                quant = stem[-2].split(".")[-1].upper() if len(stem) >= 2 else "Q4_K_M"
            else:
                quant = "Q4_K_M"

            models.append(OllamaModel(
                name         = r["id"],
                display_name = r.get("display_name", r["id"]),
                size_gb      = r.get("file_size_gb", 5.0),
                min_ram_gb   = max(r.get("file_size_gb", 5.0) * 0.8, 2.0),
                quantization = quant,
                description  = r.get("description", ""),
                last_updated = "",
            ))

        compatible   = [m for m in models if m.is_compatible(self.vram, self.ram)]
        incompatible = [m for m in models if not m.is_compatible(self.vram, self.ram)]
        return compatible + incompatible

    @property
    def downloads_via(self) -> str:
        return "huggingface_hub"