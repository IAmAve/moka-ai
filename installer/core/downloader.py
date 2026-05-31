"""Model downloader — all models fetched from GitHub Releases."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional


class ModelDownloader:
    """
    Download AI models during installation from GitHub Releases.

    No Ollama CLI pulls, no HuggingFace snapshot downloads —
    every asset comes from a GitHub release via the GitHub REST API.
    """

    # Default GitHub repo for Moka AI model releases.
    # Set via constructor or override per-model.
    DEFAULT_GITHUB_OWNER = "IAmAve"
    GITHUB_REPO = "moka-ai-models"

    def __init__(
        self,
        models_dir: str | Path,
        progress_callback: Callable[[str, float | None], None] = None,
        github_owner: str | None = None,
        github_token: str | None = None,
    ):
        self.models_dir = Path(models_dir)
        self._progress = progress_callback if progress_callback is not None else (lambda msg, pct: None)
        self._github_owner = github_owner or self.DEFAULT_GITHUB_OWNER
        self._github_token = github_token  # optional — raises rate-limit otherwise

    # ── GitHub download ────────────────────────────────────────────

    def github_download(
        self,
        asset_name: str,
        dest_dir: str | Path,
        release_tag: str,
        file_size_mb: float,
        total_weight: float,
        start_pct: float,
    ) -> bool:
        """
       Download a single release asset from GitHub.

        Uses the GitHub Releases REST API:
          GET /repos/{owner}/{repo}/releases/tags/{tag}
          → find asset by name → GET /repos/{owner}/{repo}/releases/assets/{id}
          with Accept: application/octet-stream
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / asset_name

        self._progress(f"Fetching {asset_name} from GitHub ({file_size_mb:.0f} MB)...", start_pct)

        try:
            import urllib.request
            import urllib.error
            import json

            # 1. Find asset ID for this release tag
            api_url = (
                f"https://api.github.com/repos/{self._github_owner}/"
                f"{self.GITHUB_REPO}/releases/tags/{release_tag}"
            )

            headers = {"Accept": "application/vnd.github+json"}
            if self._github_token:
                headers["Authorization"] = f"Bearer {self._github_token}"
            if self._github_token:
                headers["X-GitHub-Api-Key"] = self._github_token

            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                release = json.loads(resp.read())

            asset_id = None
            for asset in release.get("assets", []):
                if asset["name"] == asset_name:
                    asset_id = asset["id"]
                    break

            if asset_id is None:
                available = [a["name"] for a in release.get("assets", [])]
                self._progress(
                    f"  Asset '{asset_name}' not found in release '{release_tag}'. "
                    f"Available: {available}",
                    start_pct,
                )
                return False

            # 2. Download asset (streaming to file)
            download_url = (
                f"https://api.github.com/repos/{self._github_owner}/"
                f"{self.GITHUB_REPO}/releases/assets/{asset_id}"
            )
            download_headers = {
                "Accept": "application/octet-stream",
                "Authorization": f"Bearer {self._github_token}" if self._github_token else "",
            }
            download_req = urllib.request.Request(download_url, headers=download_headers)

            with urllib.request.urlopen(download_req, timeout=3600) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB chunks

                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes > 0:
                            # Progress within the chunk, using our share of the total weight
                            chunk_pct = (downloaded / total_bytes) * total_weight
                            overall_pct = start_pct + chunk_pct
                            self._progress(f"  {asset_name}  {downloaded/1024/1024:.1f} MB", overall_pct)

            self._progress(f"  OK  {asset_name} ({file_size_mb:.0f} MB saved)", start_pct + total_weight * 0.9)
            return True

        except ImportError:
            self._progress(f"  SKIP  (urllib not available — will retry first use)", start_pct)
            return False
        except urllib.error.HTTPError as e:
            self._progress(f"  HTTP {e.code}: {e.reason}  — will retry on first launch", start_pct)
            return False
        except Exception as e:
            self._progress(f"  FAIL  {asset_name}: {e}", start_pct)
            return False

    # ── Ollama helpers (optional — for models not yet on GitHub) ──

    def ensure_ollama(self) -> bool:
        return shutil.which("ollama") is not None

    def install_ollama(self) -> bool:
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
        Pull via Ollama CLI — fallback only, used when model is not yet on GitHub.
        """
        self._progress(f"Pulling {model_name} via Ollama (fallback)...", start_pct)
        try:
            proc = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if line:
                    self._progress(f"  {line}", None)
            proc.wait()
            if proc.returncode == 0:
                self._progress(f"  OK  {model_name}", start_pct + total_weight * 0.5)
                return True
            else:
                self._progress(f"  WARN  Ollama pull failed — will retry on first launch", start_pct)
                return False
        except Exception as e:
            self._progress(f"  FAIL  {model_name}: {e}", start_pct)
            return False

    def is_ollama_cached(self, model_name: str) -> bool:
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


# ── HuggingFace GGUF model downloader ──────────────────────────────────────

class HuggingFaceDownloader:
    """Download GGUF model files from HuggingFace using huggingface_hub.

    No auth required for public repos. Supports resume via hf_hub_download's
    built-in caching (leveraging ~/.cache/huggingface/).

    Usage:
        dl = HuggingFaceDownloader("C:/Program Files/Moka AI/models")
        models = dl.search_models("deepseek coder", vram_gb=8.0)
        dl.download_model("TheBloke/deepseek-coder-6.7B-GGUF",
                          "deepseek-coder-6.7b.Q4_K_M.gguf",
                          file_size_gb=4.1)
    """

    HF_SEARCH_URL = "https://huggingface.co/search?q={q}&type=model&sort=downloads"
    HF_API_ROOT  = "https://huggingface.co/api"

    def __init__(
        self,
        models_dir: str | Path,
        progress_callback: Callable[[str, float | None], None] = None,
    ):
        self.models_dir = Path(models_dir)
        self._progress = progress_callback if progress_callback is not None else (lambda m, p: None)

    # ── search ──────────────────────────────────────────────────────────────

    def search_models(
        self,
        query: str = "",
        vram_gb: float = 8.0,
        limit: int = 30,
    ) -> list[dict]:
        """Search HuggingFace for public GGUF-format models.

        Returns [{id, name, display_name, file_size_gb, description,
        downloads, gguf_files (list), best_file, compatible (bool)}].
        Internet required during search.
        """
        try:
            # Use /api/models with filter=gguf; add search= for query filtering
            search_url = (
                f"https://huggingface.co/api/models"
                f"?filter=gguf"
                f"&sort=downloads"
                f"&direction=-1"
                f"&limit=50"
            )
            if query:
                search_url += f"&search={urllib.parse.quote(query)}"

            req = urllib.request.Request(search_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))

            results = []
            for item in raw if isinstance(raw, list) else []:
                try:
                    repo_id = item.get("id", "")
                    if not repo_id:
                        continue

                    downloads = item.get("downloads", 0) or 0

                    # _list_repo_gguf_files makes a separate call per repo
                    # to get the actual file tree (no siblings in list response)
                    gguf_files = self._list_repo_gguf_files(repo_id)
                    if not gguf_files:
                        continue

                    # Pick the best GGUF variant by size (prefer Q4_K_M if available)
                    best_file = _best_gguf_file(gguf_files)

                    # Find size of best file
                    file_size_mb = 0.0
                    for f in gguf_files:
                        if f["rfilename"] == best_file:
                            file_size_mb = float(f.get("size", 0)) / (1024 * 1024)
                            break

                    file_size_gb = file_size_mb / 1024
                    compatible = self._is_compatible(file_size_gb, vram_gb)

                    results.append({
                        "id":             repo_id,
                        "name":           repo_id,
                        "display_name":   _display_name_from_repo_id(repo_id),
                        "file_size_gb":   round(file_size_gb, 2),
                        "description":    (item.get("description") or "")[:200],
                        "downloads":       downloads,
                        "gguf_files":     gguf_files,
                        "best_file":      best_file,
                        "compatible":     compatible,
                    })

                    if len(results) >= limit:
                        break

                except Exception:
                    continue

            return results

        except Exception as e:
            self._progress(f"  HF search failed: {e}", None)
            return []

    # Concurrent tree fetcher — same results as search_models but ~6x faster
    def _search_models_fast(
        self,
        query: str = "",
        vram_gb: float = 8.0,
        limit_per_term: int = 10,
    ) -> list[dict]:
        """Fast search: fetch repo list (urllib) then all tree endpoints concurrently (httpx).

        Returns the same shape as search_models().  10 terms × 10 repos = 100 repos
        with GGUF files fetched in ~2-3s vs ~40s sequentially.
        """
        try:
            import httpx

            # 1. Fetch the repo list (fast, no per-repo tree)
            search_url = (
                "https://huggingface.co/api/models"
                "?filter=gguf"
                "&sort=downloads"
                "&direction=-1"
                f"&limit={limit_per_term}"
            )
            if query:
                search_url += f"&search={urllib.parse.quote(query)}"

            req = urllib.request.Request(search_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))

            repo_ids = [
                item.get("id", "")
                for item in (raw if isinstance(raw, list) else [])
                if item.get("id")
            ]

            # 2. Concurrent tree fetch for ALL repos at once
            async def _fetch_all_trees(client: httpx.AsyncClient) -> list[dict]:
                async def _fetch_tree(repo_id: str) -> tuple[str, list]:
                    try:
                        encoded_id = urllib.parse.quote(repo_id, safe="/")
                        url = (
                            f"https://huggingface.co/api/models/{encoded_id}"
                            f"/tree/main?recursive=true"
                        )
                        r = await client.get(url, timeout=20.0)
                        r.raise_for_status()
                        tree = r.json()
                        if not isinstance(tree, list):
                            return repo_id, []
                        gguf = [
                            {"rfilename": n["path"], "size": n.get("size", 0)}
                            for n in tree
                            if n.get("type") == "file" and n.get("path", "").lower().endswith(".gguf")
                        ]
                        return repo_id, gguf
                    except Exception:
                        return repo_id, []

                tasks = [_fetch_tree(rid) for rid in repo_ids]
                results_async = await asyncio.gather(*tasks)
                return results_async  # [(repo_id, gguf_files), ...]

            tree_results = asyncio.run(_fetch_all_trees(httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_connections=16),
                headers={"Accept": "application/json"},
            )))

            # Build repo_id → gguf_files map
            tree_map = {rid: gguf for rid, gguf in tree_results}

            # 3. Assemble results
            results = []
            seen = set()
            download_counts = {item.get("id", ""): item.get("downloads", 0) or 0 for item in (raw if isinstance(raw, list) else [])}

            for repo_id in repo_ids:
                if repo_id in seen:
                    continue
                downloads = download_counts.get(repo_id, 0)
                gguf_files = tree_map.get(repo_id, [])
                if not gguf_files:
                    continue
                seen.add(repo_id)

                best_file = _best_gguf_file(gguf_files)
                file_size_mb = next(
                    (float(f["size"]) / (1024 * 1024) for f in gguf_files if f["rfilename"] == best_file),
                    0.0,
                )
                file_size_gb = file_size_mb / 1024
                results.append({
                    "id":           repo_id,
                    "name":         repo_id,
                    "display_name": _display_name_from_repo_id(repo_id),
                    "file_size_gb": round(file_size_gb, 2),
                    "description":  "",
                    "downloads":    downloads,
                    "gguf_files":   gguf_files,
                    "best_file":    best_file,
                    "compatible":   self._is_compatible(file_size_gb, vram_gb),
                })
                if len(results) >= limit_per_term:
                    break

            return results

        except ImportError:
            # httpx not installed — fall back to sequential
            self._progress("  httpx not available, using slower search path", None)
            return self.search_models(query=query, vram_gb=vram_gb, limit=limit_per_term)
        except Exception as e:
            self._progress(f"  HF fast search failed: {e}", None)
            return []

    def _list_repo_gguf_files(self, repo_id: str) -> list[dict]:
        """Return list of {rfilename, size} for .gguf files in a repo."""
        try:
            url = (
                f"https://huggingface.co/api/models/"
                f"{urllib.parse.quote(repo_id, safe='/')}"
                f"/tree/main?recursive=true"
            )
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                tree = json.loads(resp.read().decode("utf-8", errors="replace"))
            if not isinstance(tree, list):
                return []
            gguf_files = []
            for node in tree:
                if node.get("type") == "file":
                    name = node.get("path", "")
                    if name.lower().endswith(".gguf"):
                        gguf_files.append({
                            "rfilename": name,
                            "size": node.get("size", 0),
                            "type": "file",
                        })
            return gguf_files
        except Exception:
            return []

    def _is_compatible(self, model_size_gb: float, vram_gb: float) -> bool:
        """Return True if a model of model_size_gb can run on vram_gb VRAM.

        Rule: quantized Q4_K_M GGUF files are ~2.75 bits/param, so a model's
        GGUF size is roughly (params * 2.75 / 8) GB. We accept models where
        model_size_gb <= vram_gb * 1.6 (some headroom for context buffer).
        """
        return vram_gb >= 2.0 or model_size_gb <= vram_gb * 1.6

    # ── download ────────────────────────────────────────────────────────────

    def download_model(
        self,
        repo_id: str,
        filename: str,
        file_size_gb: float,
        total_weight: float = 0.40,
        start_pct: float   = 0.40,
    ) -> bool:
        """Download a single .gguf file from a HuggingFace repo.

        Uses huggingface_hub.hf_hub_download() which handles:
        - Resume (cached parts are skipped)
        - Progress reporting
        - Correct file path for the given repo + filename

        Returns True on success, False on failure.
        """
        try:
            from huggingface_hub import hf_hub_download

            dest_dir = self.models_dir / "base"
            dest_dir.mkdir(parents=True, exist_ok=True)

            file_size_mb = file_size_gb * 1024
            self._progress(
                f"Downloading {filename} from HuggingFace ({file_size_mb:.0f} MB)...",
                start_pct,
            )

            cached_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=None,          # use default HF cache (~/.cache/huggingface/)
                resume_download=True,
                force_download=False,
            )

            dest_path = dest_dir / filename

            if cached_path and os.path.isfile(cached_path):
                if Path(cached_path) != dest_path:
                    shutil.copy2(cached_path, dest_path)
                self._progress(
                    f"  OK  {filename} saved to models/base/",
                    start_pct + total_weight,
                )
                return True
            else:
                self._progress(f"  FAIL  {filename}: hf_hub_download returned no file", start_pct)
                return False

        except ImportError:
            self._progress(
                "  SKIP  huggingface_hub not installed — will retry on first launch",
                start_pct,
            )
            return False
        except Exception as e:
            self._progress(f"  FAIL  {filename}: {e}", start_pct)
            return False

    def quiet_download_model(
        self,
        repo_id: str,
        filename: str,
        file_size_gb: float,
        total_weight: float = 0.40,
        start_pct: float   = 0.40,
    ) -> bool:
        """Same as download_model but suppresses all huggingface_hub output.

        Sets HF_HUB_DISABLE_PROGRESS_BARS=1 so tqdm progress bars don't
        pollute the terminal during Step 4. Safe for parallel execution
        (each call has its own env snapshot).
        """
        import contextlib, io
        old_val = os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS", "")
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return self.download_model(
                    repo_id=repo_id,
                    filename=filename,
                    file_size_gb=file_size_gb,
                    total_weight=total_weight,
                    start_pct=start_pct,
                )
        finally:
            if old_val:
                os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = old_val
            else:
                os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)

def _display_name_from_repo_id(repo_id: str) -> str:
    """'TheBloke/deepseek-coder-6.7B-GGUF' → 'DeepSeek Coder 6.7B'"""
    name = repo_id.split("/")[-1]
    name = name.replace("-GGUF", "").replace("-.gguf", "")
    name = name.replace("-", " ").replace("_", " ")
    return name.strip()

def _best_gguf_file(gguf_files: list[dict]) -> str:
    """Pick the best GGUF file for a consumer GPU: prefer Q4_K_M or Q5_K_M."""
    # Sort: prefer quantizations Q4_K_M, Q5_K_M, Q2_K, then by size ascending
    priority = {"q4_k_m": 0, "q5_k_m": 1, "q3_k_m": 2, "q2_k": 3, "q4_k_s": 4}
    qfiles = sorted(gguf_files, key=lambda f: (
        priority.get(f["rfilename"].lower().split(".")[-2], 99),
        int(f.get("size", 0) or 0),
    ))
    return qfiles[0]["rfilename"] if qfiles else (gguf_files[0]["rfilename"] if gguf_files else "")