"""Model downloader — Ollama + HuggingFace model pull during install."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional


class ModelDownloader:
    """Download AI models during installation: Ollama base, HuggingFace image/voice."""

    def __init__(self, models_dir: str | Path, progress_callback: Callable[[str, float], None] = None):
        self.models_dir = Path(models_dir)
        self._progress = progress_callback or (lambda msg, pct: None)

    # ── Ollama ──────────────────────────────────────────────────────────────────

    def ensure_ollama(self) -> bool:
        """Check if ollama CLI is available."""
        return shutil.which("ollama") is not None

    def install_ollama(self) -> bool:
        """Install Ollama via official install script (Windows PowerShell)."""
        self._progress("Installing Ollama...", 0)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "irm https://ollama.com/install.ps1 | iex"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                self._progress("Ollama installed", 1)
                return True
            return False
        except Exception as e:
            self._progress(f"Ollama install failed: {e}", 0)
            return False

    def ollama_pull(self, model_name: str, total_weight: float, start_pct: float) -> bool:
        """
        Pull an ollama model via `ollama pull`.
        Streams stdout to the progress callback for real-time log updates.
        """
        self._progress(f"Pulling base model {model_name}...", start_pct)
        try:
            proc = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(self.models_dir),
            )
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if line:
                    self._progress(f"  {line}", None)  # log only, no pct change
            proc.wait()
            if proc.returncode == 0:
                self._progress(f"  OK  {model_name}", start_pct + total_weight * 0.5)
                return True
            else:
                self._progress(f"  WARN  ollama pull failed (will retry on first launch)", start_pct)
                return False
        except subprocess.TimeoutExpired:
            self._progress(f"  TIMEOUT  {model_name} (will retry on first launch)", start_pct)
            return False
        except Exception as e:
            self._progress(f"  FAIL  {model_name}: {e}", start_pct)
            return False

    def is_model_cached(self, model_name: str) -> bool:
        """Check if ollama model is already pulled."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return any(model_name in line for line in result.stdout.splitlines()[1:])
        except Exception:
            pass
        return False

    # ── HuggingFace ────────────────────────────────────────────────────────────

    def hf_download(self, hf_id: str, dest_dir: str, total_weight: float, start_pct: float) -> bool:
        """Download a HuggingFace model/files to dest_dir using huggingface-hub."""
        self._progress(f"Downloading {hf_id}...", start_pct)
        try:
            from huggingface_hub import snapshot_download
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)

            # Use filesystem cache + custom destination
            snapshot_download(
                repo_id=hf_id,
                cache_dir=str(dest / ".hf_cache"),
                local_dir=str(dest / hf_id.split("/")[-1]),
                local_dir_use_symlinks=False,
                resume_download=True,
                timeout=120,
            )
            self._progress(f"  OK  {hf_id}", start_pct + total_weight * 0.5)
            return True
        except ImportError:
            self._progress(f"  SKIP  huggingface-hub not available yet (will download on first use)", start_pct)
            return False
        except Exception as e:
            self._progress(f"  WARN  HF download failed: {e}", start_pct)
            return False