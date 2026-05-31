"""Moka AI Installer Wizard — Python API (PyWebView bridge)."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import tarfile
import threading
import webview
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Callable

class WizardStep(IntEnum):
    PATH = 1
    HARDWARE = 2
    MODELS = 3
    DOWNLOAD = 4
    INSTALLING = 5
    COMPLETE = 6

@dataclass
class WizardState:
    step: WizardStep = WizardStep.PATH
    install_path: str = ""
    hw_profile: dict = field(default_factory=dict)
    base_model: str = ""
    image_model: str = ""
    voice_model: str = ""
    # Tuple of (github_asset_filename, release_tag) for GitHub download
    base_model_github: tuple = field(default_factory=lambda: ("", ""))
    image_model_github: tuple = field(default_factory=lambda: ("", ""))
    voice_model_github: tuple = field(default_factory=lambda: ("", ""))
    # When non-empty: use ollama pull instead of GitHub for the base model
    ollama_model_name: str = ""
    # --- API credentials ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    custom_endpoint: str = ""
    local_only: bool = True
    github_token: str = ""  # GitHub PAT for higher-rate model releases
    # ----------------------
    download_items: list = field(default_factory=list)
    download_progress: float = 0.0
    packages: list = field(default_factory=list)
    install_progress: float = 0.0
    install_log: list = field(default_factory=list)
    shortcuts_created: bool = False
    launch_on_finish: bool = True
    auto_start_on_boot: bool = False
    error: Optional[str] = None
    _progress_callbacks: list = field(default_factory=list)
    # HuggingFace GGUF model — set by set_huggingface_model()
    _hf_repo_id:  str = ""
    _hf_filename: str = ""
    # HuggingFace image model
    _hf_image_repo_id:  str = ""
    _hf_image_filename: str = ""


# ── helpers ──────────────────────────────────────────────────────────────────

def _resolve_bundled_wav_path():
    """Resolve the path to moka_voice_ref.wav whether running dev or bundled.

    Dev:     repo_root / installer / data / xttsv2-female / moka_voice_ref.wav
    Bundled: sys._MEIPASS / installer / data / xttsv2-female / moka_voice_ref.wav
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, "installer", "data", "xttsv2-female", "moka_voice_ref.wav")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo, "installer", "data", "xttsv2-female", "moka_voice_ref.wav")


def _resolve_bundled_launcher_path():
    """Resolve the path to moka_launcher.txt whether running dev or bundled.

    Dev:     repo_root / installer / data / moka_launcher.txt
    Bundled: sys._MEIPASS / installer / data / moka_launcher.txt
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, "installer", "data", "moka_launcher.txt")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo, "installer", "data", "moka_launcher.txt")


def _resolve_bundled_main_path():
    """Resolve the path to main.py (the app entry point) whether dev or bundled.

    Dev:     repo_root / main.py
    Bundled: sys._MEIPASS / main.py  (added to extra_data in the spec)
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, "main.py")
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo, "main.py")


class WizardAPI:
    """Python-side API exposed to JS via PyWebView bridge."""
    _instance = None

    def __init__(self):
        self.state = WizardState()

    @staticmethod
    def get_instance() -> "WizardAPI":
        if WizardAPI._instance is None:
            WizardAPI._instance = WizardAPI()
        return WizardAPI._instance

    # ── State ──────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Return current wizard state for JS polling."""
        return {
            "step": self.state.step,
            "step_name": self.state.step.name.lower(),
            "install_path": self.state.install_path,
            "hw_profile": self.state.hw_profile,
            "base_model": self.state.base_model,
            "image_model": self.state.image_model,
            "voice_model": self.state.voice_model,
            "download_items": self.state.download_items,
            "download_progress": self.state.download_progress,
            "install_progress": self.state.install_progress,
            "packages": self.state.packages,
            "log": self.state.install_log,
            "error": self.state.error,
            "shortcuts_created": self.state.shortcuts_created,
        }

    def get_progress(self) -> dict:
        """Return real-time install progress for polling."""
        return {
            "step": self.state.step,
            "step_name": self.state.step.name.lower(),
            "packages": self.state.packages,
            "progress": self.state.install_progress,
            "log": self.state.install_log,
            "error": self.state.error,
        }

    # ── Welcome step ────────────────────────────────────────────────────

    def set_install_path(self, path: str) -> dict:
        """Validate the installation path. Returns {valid, path, error}."""
        path = path.strip()
        if not path:
            return {"valid": False, "path": "", "error": "Path cannot be empty."}
        self.state.install_path = path
        # Try to create it
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".moka_write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return {"valid": True, "path": path, "error": ""}
        except Exception as e:
            return {"valid": False, "path": path, "error": str(e)}

    def browse_folder(self) -> str:
        """Open native folder picker dialog and return selected path."""
        try:
            win = getattr(self, '_window', None)
            if not win:
                self.state.install_log.append("[browse] ERROR: no window reference")
                return "[ERROR:no-window]"
            result = win.create_file_dialog(
                webview.FileDialog.FOLDER,
                directory=os.path.expandvars("%USERPROFILE%"),
            )
            selected = result[0] if result else ""
            self.state.install_log.append(f"[browse] dialogReturn={selected!r} result={result!r}")
            return selected
        except Exception as e:
            import traceback
            self.state.install_log.append(f"[browse] EXCEPTION: {e}")
            self.state.install_log.append(traceback.format_exc())
            return "[ERROR:exception]"

    # ── Hardware step ──────────────────────────────────────────────────

    def scan_hardware(self) -> dict:
        """Run hardware scan on background thread. Returns updated state."""
        from installer.core.hardware import HardwareScan
        scan = HardwareScan()
        profile = scan.scan()

        # CPU label
        cpu = profile.cpu_model or "Unknown CPU"
        if profile.cpu_cores and profile.cpu_threads:
            cpu += f"  ({profile.cpu_cores}C / {profile.cpu_threads}T)"

        # OS detection
        os_label = profile.platform
        try:
            import subprocess
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject Win32_OperatingSystem).Caption"],
                capture_output=True, text=True, timeout=8,
            )
            caption = r.stdout.strip()
            if caption:
                os_label = caption
        except Exception:
            pass

        self.state.hw_profile = {
            "cpu": cpu,
            "gpu": profile.gpu_model or "No dedicated GPU",
            "vram_gb": float(profile.vram_gb) if profile.vram_gb else 0.0,
            "vram_pct": min(100.0, float(profile.vram_gb or 0) / 24.0 * 100.0),
            "ram": f"{profile.system_ram_gb:.1f} GB total · {profile.available_vram_gb:.1f} GB free",
            "os": os_label,
            "compute_capability": profile.compute_capability or "",
        }
        self.state.step = WizardStep.HARDWARE
        return self.get_state()

    # ── Models step ─────────────────────────────────────────────────────

    def get_models(self, vram_gb: float) -> list:
        """Return tiered model options for given VRAM."""
        from installer.core.models import ModelRecommender
        recon = ModelRecommender()
        recommended = recon.get_recommended_models(vram_gb)
        all_models = recon.get_all_models()

        result = []
        for mtype in ["base", "image", "voice"]:
            rec = recommended.get(mtype)
            rec_name = rec.name if rec else ""
            options = []
            for model in sorted(all_models, key=lambda m: m.size_gb):
                if model.type == mtype:
                    options.append({
                        "name": model.name,
                        "github_asset": model.github_asset,
                        "github_tag": model.github_tag,
                        "size_gb": model.size_gb,
                        "min_vram_gb": model.min_vram_gb,
                        "recommended": model.name == rec_name,
                    })
            result.append({
                "type": mtype,
                "label": {"base": "Base Model", "image": "Image Model", "voice": "Voice Model"}[mtype],
                "options": options,
                "selected": rec_name,
            })
        return result

    def set_models(self, base: str, image: str, voice: str):
        """Store selected model names from the tier-based list (GitHub download path).

        Clears ollama_model_name so the download step uses GitHub instead of Ollama pull.
        For Ollama model selection, use select_ollama_model() instead.
        """
        self.state.base_model = base
        self.state.image_model = image
        self.state.voice_model = voice
        self.state.ollama_model_name = ""  # ensure Ollama path is disabled

        from installer.core.models import ModelRecommender
        recon = ModelRecommender()
        # Build lookup: name → ModelInfo with github_asset + github_tag
        by_name = {m.name: m for m in recon.get_all_models()}
        b = by_name.get(base)
        i = by_name.get(image)
        v = by_name.get(voice)
        self.state.base_model_github     = (b.github_asset, b.github_tag) if b else (base, "v1.0")
        self.state.image_model_github    = (i.github_asset, i.github_tag) if i else (image, "v1.0")
        self.state.voice_model_github    = (v.github_asset, v.github_tag) if v else (voice, "v1.0")

    def set_api_config(self, openai_key: str = "", anthropic_key: str = "",
                       custom_endpoint: str = "", local_only: bool = True,
                       github_token: str = ""):
        """Store API credentials and settings."""
        self.state.openai_api_key = openai_key
        self.state.anthropic_api_key = anthropic_key
        self.state.custom_endpoint = custom_endpoint
        self.state.local_only = local_only
        self.state.github_token = github_token

    def search_ollama_models(self, query: str = "") -> list[dict]:
        """Search Ollama library for models compatible with the user's hardware.

        Requires internet during installation. After install Moka runs offline.
        Returns list of {name, display_name, size_gb, min_ram_gb, quantization,
        compatible, description} sorted by hardware compatibility.
        """
        hw = self.state.hw_profile
        vram = float(hw.get("vram_gb", 8.0)) if hw else 8.0
        ram = 16.0

        def _log(msg):
            pass

        from installer.core.models import OllamaCatalog
        catalog = OllamaCatalog(vram_gb=vram, system_ram_gb=ram, logger=_log)
        models = catalog.search(query)
        return [
            {
                "name": m.name,
                "display_name": m.display_name,
                "size_gb": m.size_gb,
                "min_ram_gb": m.min_ram_gb,
                "quantization": m.quantization,
                "description": m.description,
                "compatible": m.is_compatible(vram, ram),
            }
            for m in models
        ]

    def search_huggingface_models(self, query: str = "") -> list[dict]:
        """Search HuggingFace for public GGUF models matching the user's GPU.

        Requires internet during installation. Uses HF Hub search API.
        Returns list of {id, name, display_name, file_size_gb, downloads,
        gguf_files, best_file, compatible, description}.
        """
        hw    = self.state.hw_profile
        vram  = float(hw.get("vram_gb", 8.0)) if hw else 8.0
        from installer.core.downloader import HuggingFaceDownloader
        dl = HuggingFaceDownloader(models_dir="", progress_callback=lambda m, p: None)
        return dl.search_models(query=query, vram_gb=vram, limit=30)

    def get_huggingface_models_all(self, vram_gb: float = 8.0) -> list[dict]:
        """Return GGUF models formatted for the Step 3 dropdown.

        Uses concurrent async I/O (httpx) to fetch all repo trees in parallel,
        giving ~100 models in 3-5s instead of 60s sequentially.

        Separately searches base (text/coding) and image model families,
        deduplicated across all queries.

        Requires internet during install. Returns fully offline after install.
        """
        import concurrent.futures
        from installer.core.downloader import HuggingFaceDownloader
        dl = HuggingFaceDownloader(models_dir="", progress_callback=lambda m, p: None)
        vram = float(vram_gb)

        ALL_TEXT_TERMS = [
            "llama", "deepseek", "qwen", "mistral",
            "codellama", "starcoder", "granite",
            "phi", "gemma", "minicpm",
        ]
        ALL_IMAGE_TERMS = [
            "sdxl", "stable-diffusion", "flux",
            "sdxl-turbo", "wan",
        ]

        def fetch_all(terms: list[str], limit_per_term: int = 8) -> list[dict]:
            """Fetch multiple terms in parallel using ThreadPoolExecutor.
            All tree calls within each term are also concurrent (httpx async).
            Total wall-clock: ~3-5s for 100 repos vs ~60s sequential.
            """
            results = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(terms), 6)) as ex:
                futures = {
                    ex.submit(dl._search_models_fast, term, vram, limit_per_term): term
                    for term in terms
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        found = future.result() or []
                        for m in found:
                            repo_id = m.get("id", "")
                            if repo_id and repo_id not in results:
                                results[repo_id] = m
                    except Exception:
                        pass
            return list(results.values())

        # Fetch all terms in parallel (6 workers, ~10 terms each)
        base_models  = fetch_all(ALL_TEXT_TERMS,  limit_per_term=8)
        image_models = fetch_all(ALL_IMAGE_TERMS, limit_per_term=6)

        def fmt(models, mtype):
            out = []
            seen = set()
            for m in models:
                repo_id    = m.get("id", "")
                best_file  = m.get("best_file", "")
                size_gb    = m.get("file_size_gb", 0)
                disp       = m.get("display_name", repo_id)
                if repo_id in seen or not best_file:
                    continue
                seen.add(repo_id)
                compat = m.get("compatible", True)
                badge  = "★ Compatible" if compat else "⚠ Large for VRAM"
                label  = f"{disp} ({size_gb:.1f} GB) — {badge}"
                out.append({
                    "value":      repo_id,
                    "label":      label,
                    "size_gb":    size_gb,
                    "type":       mtype,
                    "repo_id":    repo_id,
                    "gguf_file":  best_file,
                    "downloads":  m.get("downloads", 0),
                    "compatible": compat,
                    "description": (m.get("description") or "")[:120],
                })
            return out

        return fmt(base_models, "base") + fmt(image_models, "image")

    def set_huggingface_model(self, repo_id: str, filename: str, display_name: str):
        """Set the base model to be downloaded from HuggingFace (GGUF).

        Clears ollama_model_name and base_model_github so _do_download
        routes to HuggingFaceDownloader instead of Ollama or GitHub.
        """
        self.state.ollama_model_name  = ""
        self.state.base_model         = display_name
        self.state.base_model_github  = ("", "")
        self.state._hf_repo_id        = repo_id
        self.state._hf_filename       = filename

    def set_huggingface_image_model(self, repo_id: str, filename: str, display_name: str):
        """Set the image model to be downloaded from HuggingFace (image pipeline).

        Stores in _hf_image_repo_id / _hf_image_filename so _do_download
        uses HuggingFaceDownloader for the image model instead of GitHub.
        """
        self.state.image_model         = display_name
        self.state.image_model_github  = ("", "")
        self.state._hf_image_repo_id   = repo_id
        self.state._hf_image_filename  = filename

    def set_auto_start(self, enabled: bool):
        """Enable or disable auto-start on Windows boot."""
        self.state.auto_start_on_boot = enabled

    def select_ollama_model(self, model_name: str):
        """Set the base model to be downloaded via `ollama pull` instead of GitHub.

        Moka will use Ollama as the inference runtime (ollama serve) instead of
        loading GGUF directly with llama.cpp. After install, Ollama daemon runs
        in the background and Moka connects to localhost:11434.
        """
        self.state.ollama_model_name = model_name
        self.state.base_model = model_name
        # Clear GitHub tuple so start_download knows to use Ollama instead
        self.state.base_model_github = ("", "")

    # ── Download step (step 4) ─────────────────────────────────────

    def start_download(self):
        """Begin downloading all components (Python, models, voice, deps)."""
        if getattr(self, "_download_running", False):
            return
        self._download_running = True
        t = threading.Thread(target=self._do_download, daemon=True)
        t.start()

    def _do_download(self):
        from installer.core.deps import DepResolver

        self.state.step = WizardStep.DOWNLOAD
        self.state.install_log = []
        self.state.packages = []
        self.state.install_progress = 0.0
        self.state.download_progress = 0.0

        models_dir = os.path.join(self.state.install_path, "models")
        os.makedirs(models_dir, exist_ok=True)

        def log(msg: str):
            self.state.install_log.append(msg)

        def prog(pct: float):
            self.state.download_progress = pct

        try:
            # ── 1. Python + pip packages ───────────────────────────────────
            resolver = DepResolver()
            packages = resolver.resolve(
                require_voice=bool(self.state.voice_model),
                require_image=bool(self.state.image_model),
            )
            self.state.packages = [
                {"name": p.name, "status": "pending", "error": ""}
                for p in packages
            ]
            self.state.download_items = [
                {"id": "python",      "label": "Python Runtime", "downloaded": 0, "total": 80,  "status": "pending"},
                {"id": "model-base",  "label": "Coding Model",   "downloaded": 0, "total": int(self._model_size(self.state.base_model)),  "status": "pending"},
                {"id": "model-image", "label": "Image Model",    "downloaded": 0, "total": int(self._model_size(self.state.image_model)), "status": "pending"},
                {"id": "deps",        "label": "Dependencies",   "downloaded": 0, "total": 500, "status": "pending"},
            ]

            prog(0.05)
            log("Downloading Python and dependencies...")

            to_install = [p for p in packages if p.install_action in ("install", "upgrade")]
            total_pkgs = len(to_install) or 1

            # Iterate original package list — pkg_idx stays in sync with self.state.packages
            install_seq = 0
            for pkg_idx, pkg in enumerate(packages):
                if pkg.install_action not in ("install", "upgrade"):
                    continue

                # Map pip package index to a download UI item (python or deps)
                pip_item = self.state.download_items[0] if self.state.download_items else None
                pkg.status = "installing"
                self.state.packages[pkg_idx]["status"] = "installing"
                if pip_item:
                    pip_item["status"] = "downloading"
                log(f"Installing {pkg.name}...")
                try:
                    result = resolver.install_packages(
                        [pkg],
                        progress_callback=lambda p, m: log(m),
                    )
                    if result[0].status == "done":
                        pkg.status = "done"
                        self.state.packages[pkg_idx]["status"] = "done"
                        if pip_item:
                            pip_item["status"] = "done"
                            pip_item["downloaded"] = pip_item["total"]
                        log(f"  OK  {pkg.name}")
                    else:
                        pkg.status = "failed"
                        self.state.packages[pkg_idx]["status"] = "failed"
                        self.state.packages[pkg_idx]["error"] = pkg.error
                        log(f"  FAIL  {pkg.name}")
                except Exception as e:
                    pkg.status = "failed"
                    self.state.packages[pkg_idx]["status"] = "failed"
                    self.state.packages[pkg_idx]["error"] = str(e)
                    log(f"  FAIL  {pkg.name}: {e}")

                install_seq += 1
                self.state.download_progress = 0.05 + (install_seq / total_pkgs) * 0.20
                if install_seq == total_pkgs:
                    log("  All packages ready.")

            # Mark python done
            if self.state.download_items and self.state.download_items[0]["id"] == "python":
                self.state.download_items[0]["status"] = "done"
                self.state.download_items[0]["downloaded"] = self.state.download_items[0]["total"]

            # ── 2. Download models from GitHub Releases ─────────────────────
            from installer.core.downloader import ModelDownloader, HuggingFaceDownloader
            github_token = getattr(self.state, "github_token", "") or None
            downloader = ModelDownloader(
                models_dir,
                progress_callback=lambda m, p: (log(m), prog(p) if p else None) and None,
                github_token=github_token,
            )

            # 2a. Base model (Ollama pull OR GitHub download)
            ollama_name = self.state.ollama_model_name
            base_model = self.state.base_model
            base_item = next((d for d in self.state.download_items if d["id"] == "model-base"), None) if self.state.download_items else None

            if ollama_name:
                # Use Ollama — pull from library (internet during install, offline at runtime)
                if base_item:
                    base_item["status"] = "downloading"
                log(f"Downloading base model via Ollama: {ollama_name}")
                from installer.core.models import OllamaCatalog
                hw = self.state.hw_profile
                vram = float(hw.get("vram_gb", 8.0)) if hw else 8.0
                catalog = OllamaCatalog(vram_gb=vram, system_ram_gb=16.0, logger=log)
                ok = catalog.pull(
                    ollama_name,
                    progress_callback=lambda msg, pct: (log(msg), prog(pct) if pct else None),
                    total_weight=0.30,
                    start_pct=0.40,
                )
                if not ok:
                    log(f"  FAIL  Ollama pull failed — will retry on first launch")
                    if base_item:
                        base_item["status"] = "pending"
                        base_item["downloaded"] = 0
                else:
                    if base_item:
                        base_item["status"] = "done"
                        base_item["downloaded"] = base_item["total"]
                prog(0.70)
            elif getattr(self.state, "_hf_repo_id", None) and base_model:
                # ── HuggingFace base model download (potentially parallel with image) ──
                # If image model is also HF, both download concurrently via ThreadPoolExecutor.
                # quiet_download_model uses HF_HUB_DISABLE_PROGRESS_BARS=1 so no terminal pop-up.
                from concurrent.futures import ThreadPoolExecutor, as_completed

                hf_base = {
                    "repo_id":  self.state._hf_repo_id,
                    "filename": self.state._hf_filename,
                    "item":     base_item,
                    "log":      [],
                }
                hf_img_data = None
                if getattr(self.state, "_hf_image_repo_id", None) and image_model:
                    hf_img_data = {
                        "repo_id":  self.state._hf_image_repo_id,
                        "filename": getattr(self.state, "_hf_image_filename", "") or "model.gguf",
                        "item":     img_item,
                        "log":      [],
                    }

                def quiet_dl_base():
                    hf_dl = HuggingFaceDownloader(
                        models_dir,
                        progress_callback=lambda m, p: (hf_base["log"].append(m), prog(p) if p else None),
                    )
                    return hf_dl.quiet_download_model(
                        repo_id     = hf_base["repo_id"],
                        filename    = hf_base["filename"],
                        file_size_gb = self._model_size(self.state.base_model) / 1024.0,
                        total_weight = 0.30,
                        start_pct    = 0.40,
                    )

                def quiet_dl_image():
                    hf_dl_img = HuggingFaceDownloader(
                        models_dir,
                        progress_callback=lambda m, p: (hf_img_data["log"].append(m), prog(p) if p else None),
                    )
                    return hf_dl_img.quiet_download_model(
                        repo_id     = hf_img_data["repo_id"],
                        filename    = hf_img_data["filename"],
                        file_size_gb = self._model_size(image_model) / 1024.0,
                        total_weight = 0.10,
                        start_pct    = 0.65,
                    )

                if hf_img_data and base_item:
                    # Both base and image from HF — download in parallel
                    for item in [base_item, img_item]:
                        if item: item["status"] = "downloading"
                    log(f"Downloading models from HuggingFace (base + image in parallel)...")

                    base_ok = False
                    with ThreadPoolExecutor(max_workers=2) as ex:
                        f_base  = ex.submit(quiet_dl_base)
                        f_image = ex.submit(quiet_dl_image)
                        base_ok = f_base.result()
                        img_ok  = f_image.result()

                    if base_item:
                        base_item["status"] = "done" if base_ok else "failed"
                        base_item["downloaded"] = base_item["total"] if base_ok else 0
                    if img_item:
                        img_item["status"] = "done" if img_ok else "failed"
                        img_item["downloaded"] = img_item["total"] if img_ok else 0
                    if not base_ok:
                        log("  FAIL  Base model HF download failed — check network")
                    if not img_ok:
                        log("  WARN  Image model HF download failed — will use fallback on first run")
                    prog(1.0)
                else:
                    # Base only (image is GitHub or not selected)
                    if base_item: base_item["status"] = "downloading"
                    log(f"Downloading base model from HuggingFace: {hf_base['repo_id']}/{hf_base['filename']}")
                    base_ok = quiet_dl_base()
                    if base_item:
                        base_item["status"] = "done" if base_ok else "failed"
                        base_item["downloaded"] = base_item["total"] if base_ok else 0
                    if not base_ok:
                        log("  FAIL  HuggingFace download failed — check network or asset")
                    prog(0.70)

                    # Single pass: mark deps done, jump to 1.0
                    deps_item = next((d for d in self.state.download_items if d["id"] == "deps"), None)
                    if deps_item:
                        deps_item["status"] = "done"
                        deps_item["downloaded"] = deps_item["total"]
                    self.state.download_progress = 1.0
                    return  # bail out of _do_download early — everything parallelised
            elif base_model:
                github_asset, github_tag = self.state.base_model_github or (base_model, "v1.0")
                log(f"Downloading base model from GitHub: {github_asset}")
                ok = downloader.github_download(
                    asset_name=github_asset,
                    dest_dir=os.path.join(models_dir, "base"),
                    release_tag=github_tag,
                    file_size_mb=self._model_size(base_model),
                    total_weight=0.25,
                    start_pct=0.40,
                )
                if base_item:
                    if ok:
                        base_item["status"] = "done"
                        base_item["downloaded"] = base_item["total"]
                    else:
                        base_item["status"] = "failed"
                        base_item["downloaded"] = 0
                        log(f"  FAIL  GitHub asset '{github_asset}' not found or download error. "
                            f"Verify the asset exists at github.com/{downloader._github_owner}/{downloader.GITHUB_REPO}/releases/{github_tag}")
                prog(0.65)

            # 2b. Image model (HF GGUF OR GitHub)
            image_model = self.state.image_model
            if image_model:
                img_dir = os.path.join(models_dir, "image")
                img_item = next((d for d in self.state.download_items if d["id"] == "model-image"), None)
                if img_item:
                    img_item["status"] = "downloading"

                hf_img_repo = getattr(self.state, "_hf_image_repo_id", None)
                if hf_img_repo:
                    # HuggingFace image model download
                    hf_img_file = getattr(self.state, "_hf_image_filename", "") or "model.gguf"
                    log(f"Downloading image model from HuggingFace: {hf_img_repo}/{hf_img_file}")
                    hf_dl_img = HuggingFaceDownloader(
                        models_dir,
                        progress_callback=lambda m, p: (log(m), prog(p) if p else None),
                    )
                    img_ok = hf_dl_img.download_model(
                        repo_id=hf_img_repo,
                        filename=hf_img_file,
                        file_size_gb=self._model_size(image_model) / 1024.0,
                        total_weight=0.10,
                        start_pct=0.65,
                    )
                    if img_item:
                        img_item["status"] = "done" if img_ok else "failed"
                        img_item["downloaded"] = img_item["total"] if img_ok else 0
                    if not img_ok:
                        log(f"  WARN  Image HF download failed — will use fallback on first run")
                else:
                    # GitHub fallback
                    github_asset, github_tag = getattr(self.state, "image_model_github", (image_model, "v1.0"))
                    log(f"Downloading image model from GitHub: {github_asset}")
                    img_ok = downloader.github_download(
                        asset_name=github_asset,
                        dest_dir=img_dir,
                        release_tag=github_tag,
                        file_size_mb=self._model_size(image_model),
                        total_weight=0.10,
                        start_pct=0.65,
                    )
                    if img_item:
                        img_item["status"] = "done" if img_ok else "failed"
                        img_item["downloaded"] = img_item["total"] if img_ok else 0

            # mark deps done
            deps_item = next((d for d in self.state.download_items if d["id"] == "deps"), None)
            if deps_item:
                deps_item["status"] = "done"
                deps_item["downloaded"] = deps_item["total"]

            prog(1.0)
            self.state.download_progress = 1.0
            self.state.step = WizardStep.INSTALLING
            log("DOWNLOAD COMPLETE")
            # Signal JS to move to step 5

        except Exception as e:
            import traceback
            self.state.error = str(e)
            self.state.install_log.append(f"FATAL ERROR: {e}")
            self.state.install_log.append(traceback.format_exc())
            self.state.step = WizardStep.INSTALLING
        finally:
            self._download_running = False

    def _model_size(self, name: str) -> float:
        """Return actual download size in MB from tiers.yaml, name-based fallback,
        or by extracting (X.X GB) from HF-formatted display labels."""
        import re
        if not name:
            return 2000.0
        # Extract "(X.X GB)" from HF dropdown labels like "Deepseek 6.7B (4.1 GB) — ★ Compatible"
        m = re.search(r"\((\d+(?:.\d+)?)\s*GB\)", name)
        if m:
            return float(m.group(1)) * 1024
        try:
            from installer.core.models import ModelRecommender
            recon = ModelRecommender()
            all_models = {m.name: m.size_gb * 1024 for m in recon.get_all_models()}
            if name in all_models:
                return all_models[name]
        except Exception:
            pass
        sizes = {
            "llama3.2": 700,
            "llama3.1": 5000,
            "mistral": 4100,
            "qwen2.5": 4000,
            "sd-turbo": 1600,
            "sdxl": 6500,
            "silero": 150,
            "deepseek": 4000,
        }
        nl = (name or "").lower()
        for k, v in sizes.items():
            if k in nl:
                return float(v)
        return 2000.0

    # ── Install step (step 5) ─────────────────────────────────────

    def start_install(self):
        """Start the installation phase (config writing, shortcuts)."""
        if getattr(self, "_install_running", False):
            return
        self._install_running = True
        t = threading.Thread(target=self._do_install, daemon=True)
        t.start()

    def _do_install(self):
        from installer.core.writer import ConfigWriter

        self.state.step = WizardStep.INSTALLING
        self.state.install_log = []
        self.state.packages = []
        self.state.install_progress = 0.0

        def log(msg: str):
            self.state.install_log.append(msg)

        def prog(pct: float):
            self.state.install_progress = pct

        try:
            log("Installing Moka AI...")

            # Mark all packages as done (already downloaded / installed by _do_download)
            for i, pkg in enumerate(self.state.packages):
                self.state.packages[i]["status"] = "done"
            prog(0.10)

            # ── Credentials ──────────────────────────────────────────────
            try:
                ConfigWriter().write_credentials(
                    path=self.state.install_path,
                    openai_api_key=self.state.openai_api_key,
                    anthropic_api_key=self.state.anthropic_api_key,
                    custom_endpoint=self.state.custom_endpoint,
                    local_only=self.state.local_only,
                )
                log("  OK  Credentials saved")
            except Exception as e:
                log(f"  WARN  Credentials save: {e}")

            prog(0.50)

            # ── Config ──────────────────────────────────────────────────
            log("Writing config files...")
            hw = self.state.hw_profile
            try:
                ConfigWriter().write(
                    install_path=self.state.install_path,
                    base_model=self.state.base_model,
                    image_model=self.state.image_model,
                    voice_model=self.state.voice_model,
                    gpu_model=hw.get("gpu", "Unknown"),
                    vram_gb=hw.get("vram_gb", 0.0),
                    compute_capability=hw.get("compute_capability"),
                )
                log("  OK  Config files written")
                prog(0.90)
            except Exception as e:
                log(f"  WARN  Config write failed: {e}")

            # ── Moka AI launcher ─────────────────────────────────────────
            try:
                launcher_src = _resolve_bundled_launcher_path()
                launcher_dst = os.path.join(self.state.install_path, "moka.py")
                if launcher_src and os.path.isfile(launcher_src):
                    shutil.copy2(launcher_src, launcher_dst)
                    log("  OK  Moka AI launcher written")
                else:
                    log("  WARN  moka_launcher.txt not in bundle — launcher may be missing")
            except Exception as e:
                log(f"  WARN  Launcher write: {e}")

            # ── App entry point (main.py) — copy to install dir ───────────
            try:
                main_src = _resolve_bundled_main_path()
                main_dst = os.path.join(self.state.install_path, "main.py")
                if main_src and os.path.isfile(main_src):
                    shutil.copy2(main_src, main_dst)
                    log("  OK  Moka AI main.py written")
                else:
                    log("  WARN  main.py not found — app entry point missing")
            except Exception as e:
                log(f"  WARN  main.py write: {e}")

            # ── Copy full bundled runtime tree to install dir ─────────────
            try:
                import sys as _sys_bundle
                meipass = getattr(_sys_bundle, "_MEIPASS", None)
                if meipass:
                    def _skip_installer_entries(src, names):
                        skip = {"installer", "installer_wizard", "__pycache__", ".git", ".github"}
                        return {n for n in names if n in skip}
                    shutil.copytree(
                        meipass, self.state.install_path,
                        dirs_exist_ok=True,
                        ignore=_skip_installer_entries,
                    )
                    log("  OK  Runtime tree installed")
                else:
                    log("  WARN  dev mode — runtime tree copy skipped (not bundled)")
            except Exception as e:
                log(f"  WARN  Runtime tree: {e}")

            # ── Voice ref wav — bundled in installer, copy to install dir ──
            try:
                bundled_wav = _resolve_bundled_wav_path()
                voice_dest_dir = os.path.join(self.state.install_path, "models", "voice", "xttsv2-female")
                if bundled_wav and os.path.isfile(bundled_wav):
                    os.makedirs(voice_dest_dir, exist_ok=True)
                    shutil.copy2(bundled_wav, os.path.join(voice_dest_dir, "moka_voice_ref.wav"))
                    log("  OK  Moka voice embedded")
                else:
                    log("  WARN  moka_voice_ref.wav not in bundle")
            except Exception as e:
                log(f"  WARN  Voice embed: {e}")

            # (Auto-start task is created in create_shortcuts_and_launch instead.)

            prog(1.0)
            self.state.step = WizardStep.COMPLETE
            self.state.install_progress = 1.0
            log("INSTALL COMPLETE")

        except Exception as e:
            import traceback
            self.state.error = str(e)
            self.state.install_log.append(f"FATAL ERROR: {e}")
            self.state.install_log.append(traceback.format_exc())
            self.state.step = WizardStep.COMPLETE
            self.state.install_progress = 1.0
        finally:
            self._install_running = False

    def _log_config(self, msg: str):
        self.state.install_log.append(msg)

    def register_uninstaller(self, version: str) -> bool:
        """Register uninstaller in Windows Add/Remove Programs."""
        try:
            from installer.core.writer import ConfigWriter
            ConfigWriter().register_uninstaller(self.state.install_path, version)
            return True
        except Exception:
            return False

    # ── Finish step ──────────────────────────────────────────────────────

    def create_shortcuts_and_launch(self, desktop: bool, startmenu: bool,
                                    launch: bool, auto_start: bool = False):
        """Create shortcuts and optionally launch Moka AI, then close."""
        from installer.core.shortcuts import Shortcuts

        path = self.state.install_path
        if not path:
            return

        sc = Shortcuts(path)
        if desktop:
            try:
                sc.create_desktop_shortcut()
                self.state.install_log.append("Desktop shortcut created.")
            except Exception as e:
                self.state.install_log.append(f"Shortcut (desktop): {e}")
        if startmenu:
            try:
                sc.create_start_menu_shortcut()
                self.state.install_log.append("Start Menu shortcut created.")
            except Exception as e:
                self.state.install_log.append(f"Shortcut (start menu): {e}")

        self.state.shortcuts_created = True

        # Auto-start task (user confirmed on finish screen checkbox)
        if auto_start:
            try:
                if sc.create_auto_start_task():
                    self.state.install_log.append("Auto-start task registered.")
            except Exception as e:
                self.state.install_log.append(f"Auto-start task: {e}")

        if launch:
            try:
                import subprocess as _subprocess, sys as _sys
                moka_py = os.path.join(path, "moka.py")
                _subprocess.Popen(
                    [_sys.executable, moka_py],
                    cwd=path,
                    creationflags=getattr(_subprocess, "DETACHED_PROCESS", 0) if _sys.platform == "win32" else 0,
                    stdout=_subprocess.DEVNULL,
                    stderr=_subprocess.DEVNULL,
                )
                self.state.install_log.append("Moka AI launched.")
            except Exception as e:
                self.state.install_log.append(f"Launch: {e}")

    def run_self_diagnostics(self) -> dict:
        """Run offline diagnostics on the installed Moka AI environment.

        Checks: config files, models directory, pip packages, GPU availability,
        disk space, and shortcut files. Returns {"ok": bool, "log": [str]}.
        """
        log_lines = []
        install_path = self.state.install_path

        _ok = [True]

        def log(msg: str, ok: bool = True):
            prefix = "  OK  " if ok else "  FAIL  "
            log_lines.append(prefix + msg)
            if not ok:
                _ok[0] = False

        log("=== Moka AI Self-Diagnostics ===")

        # 1. Config directory
        config_dir = os.path.join(install_path, "config")
        if os.path.isdir(config_dir):
            try:
                config_files = os.listdir(config_dir)
                log(f"Config dir OK ({len(config_files)} files: {', '.join(config_files)})")
            except Exception as e:
                log(f"Config dir error: {e}", ok=False)
        else:
            log("Config directory not found", ok=False)

        # 2. Models directory
        models_dir = os.path.join(install_path, "models")
        if os.path.isdir(models_dir):
            try:
                model_subdirs = os.listdir(models_dir)
                log(f"Models dir OK ({len(model_subdirs)} subdirs)")
            except Exception as e:
                log(f"Models dir error: {e}", ok=False)
        else:
            log("Models directory not found", ok=False)

        # 3. Base model presence
        base_model_dir = os.path.join(models_dir, "base")
        if os.path.isdir(base_model_dir):
            try:
                base_files = os.listdir(base_model_dir)
                log(f"Base model: {len(base_files)} item(s) present")
            except Exception:
                log("Base model dir unreadable", ok=False)
        else:
            log("Base model dir empty — will download on first run", ok=False)

        # 4. Voice model presence
        voice_model_dir = os.path.join(models_dir, "voice")
        if os.path.isdir(voice_model_dir):
            try:
                voice_files = os.listdir(voice_model_dir)
                log(f"Voice model: {len(voice_files)} item(s) present")
            except Exception:
                log("Voice model dir unreadable", ok=False)
        else:
            log("Voice model dir empty — will download on first run", ok=False)

        # 5. pip environment
        try:
            import importlib.metadata
            installed_pkgs = {d.name.lower(): d.version for d in importlib.metadata.distributions()}
            critical = ['torch', 'transformers', 'flask', 'requests']
            for pkg in critical:
                if pkg in installed_pkgs:
                    log(f"pip: {pkg}=={installed_pkgs[pkg]}")
                else:
                    log(f"pip: {pkg} NOT FOUND", ok=False)
        except Exception as e:
            log(f"pip check failed: {e}", ok=False)

        # 6. GPU still detectable
        try:
            from installer.core.hardware import HardwareScan
            scan = HardwareScan()
            profile = scan.scan()
            if profile.gpu_model and profile.gpu_model != "No GPU detected":
                log(f"GPU: {profile.gpu_model} ({profile.vram_gb} GB VRAM)")
                if profile.compute_capability:
                    log(f"  Compute capability: {profile.compute_capability}")
            else:
                log("No GPU detected (CPU-only mode will work)", ok=False)
        except Exception as e:
            log(f"GPU scan: {e}", ok=False)

        # 7. Disk space
        try:
            import psutil
            free_gb = psutil.disk_usage(install_path).free / (1024**3)
            log(f"Disk free: {free_gb:.1f} GB")
            if free_gb < 5:
                log("Disk space low (< 5 GB free)", ok=False)
        except Exception as e:
            log(f"Disk check: {e}", ok=False)

        # 8. Shortcuts
        shortcuts_ok = self.state.shortcuts_created
        log(f"Shortcuts created: {'Yes' if shortcuts_ok else 'No (optional)'}")

        log("=== Diagnostics Complete ===")
        return {"ok": _ok[0], "log": log_lines}

    def self_fix(self) -> dict:
        """Deprecated — use run_self_diagnostics instead."""
        return self.run_self_diagnostics()

    def undo_install(self) -> dict:
        """Remove Moka AI installation directory and unregister shortcuts."""
        try:
            from installer.core.uninstaller import UninstallerCore
            path = self.state.install_path
            if not path:
                return {"ok": False, "error": "No install path set"}
            uninstaller = UninstallerCore(path)
            result = uninstaller.run()
            return {"ok": True, "details": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def speak_text(self, text: str) -> dict:
        """Synthesize speech using pyttsx3 via subprocess (runs safely from bg thread).

        Returns {"ok": True} on success, {"ok": False, "error": "..."} on failure.
        """
        import subprocess, sys
        script = (
            "import sys\\n"
            "try:\\n"
            "    import pyttsx3\\n"
            "    engine = pyttsx3.init()\\n"
            "    engine.setProperty('rate', 160)\\n"
            "    engine.setProperty('volume', 1.0)\\n"
            "    voices = engine.getProperty('voices')\\n"
            "    if voices:\\n"
            "        engine.setProperty('voice', voices[0].id)\\n"
            "    engine.say(" + repr(text) + ")\\n"
            "    engine.runAndWait()\\n"
            "    engine.stop()\\n"
            "    sys.exit(0)\\n"
            "except Exception as e:\\n"
            "    sys.exit(1)\\n"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0:
                return {"ok": True}
            return {"ok": False, "error": "TTS subprocess returned non-zero"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "TTS timed out"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def debug_info(self) -> str:
        has_window = getattr(self, '_window', None) is not None
        return f"step={self.state.step.name} step_name={self.state.step.name.lower()} has_window={has_window}"

    # ── Window controls (frameless title bar) ──────────────────────
    def minimize_window(self) -> bool:
        """Minimize the application window."""
        try:
            win = getattr(self, '_window', None)
            if win:
                win.minimize()
                return True
        except Exception:
            pass
        return False

    def maximize_window(self) -> bool:
        """Toggle maximize / restore the window."""
        try:
            win = getattr(self, '_window', None)
            if win:
                if getattr(self, '_window_maximized', False):
                    win.restore()
                    self._window_maximized = False
                else:
                    win.maximize()
                    self._window_maximized = True
                return True
        except Exception:
            pass
        return False

    def close_window(self) -> bool:
        """Close the application window."""
        try:
            win = getattr(self, '_window', None)
            if win:
                win.destroy()
                return True
        except Exception:
            pass
        return False
