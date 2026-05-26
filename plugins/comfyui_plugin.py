"""
ComfyUI Plugin for MOKA AI

Launches ComfyUI workflows and manages the local AI image generation
server. Requires filesystem and network permissions.
"""

import subprocess
import os
import time
import requests
from typing import Any, Callable, Dict, Optional

from plugins.base_plugin import MokaPlugin, PluginMetadata, PluginPermissions


class ComfyUIPlugin(MokaPlugin):
    DEFAULT_PORT = 8188
    DEFAULT_HOST = "http://localhost"

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="comfyui",
            version="1.0.0",
            description="ComfyUI launcher — start local server, queue workflows",
            author="MOKA",
            dependencies=["requests"],
        )

    @property
    def permissions(self) -> PluginPermissions:
        return PluginPermissions(filesystem=True, network=True, process_management=True)

    def __init__(self, config: Dict[str, Any] = None, logger: Callable = None):
        super().__init__(config, logger)
        self._server_process: Optional[subprocess.Popen] = None
        self._server_url = f"{self.DEFAULT_HOST}:{self.DEFAULT_PORT}"

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        action = data.get("action", "start")
        if action == "start":
            return self._start_server(data)
        elif action == "stop":
            return self._stop_server(data)
        elif action == "status":
            return self._server_status(data)
        elif action == "queue":
            return self._queue_workflow(data)
        return {"ok": False, "error": f"unknown action: {action}"}

    def _find_comfyui_path(self) -> Optional[str]:
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\ComfyUI\main.py"),
            os.path.expandvars(r"%USERPROFILE%\ComfyUI\main.py"),
            os.path.join(os.getcwd(), "ComfyUI", "main.py"),
            os.path.join(os.getcwd(), "main.py"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _start_server(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._server_process is not None:
            return {"ok": True, "message": "ComfyUI server already running", "url": self._server_url}

        comfyui_main = self._find_comfyui_path()
        if not comfyui_main:
            return {"ok": False, "error": "ComfyUI not found — install at ComfyUI/main.py or ComfyUI in cwd"}

        port = data.get("port", self.DEFAULT_PORT)
        try:
            self._server_process = subprocess.Popen(
                ["python", comfyui_main, "--port", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._server_url = f"http://localhost:{port}"
            # Wait briefly for server startup
            time.sleep(5)
            self._log(f"ComfyUI server started: {self._server_url}")
            return {"ok": True, "url": self._server_url, "pid": self._server_process.pid}
        except Exception as e:
            self._server_process = None
            return {"ok": False, "error": str(e)}

    def _stop_server(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._server_process is None:
            return {"ok": True, "message": "ComfyUI server not running"}
        try:
            self._server_process.terminate()
            self._server_process.wait(timeout=10)
            self._server_process = None
            self._log("ComfyUI server stopped")
            return {"ok": True, "action": "stop"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _server_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        port = data.get("port", self.DEFAULT_PORT)
        url = f"http://localhost:{port}/system_stats"
        try:
            response = requests.get(url, timeout=5)
            return {
                "ok": response.ok,
                "url": url,
                "status": response.status_code,
                "response": response.json() if response.ok else None,
            }
        except requests.ConnectionError:
            return {"ok": False, "url": url, "message": "server not reachable"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _queue_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_json = data.get("workflow_json")
        port = data.get("port", self.DEFAULT_PORT)
        url = f"http://localhost:{port}/prompt"

        if workflow_json:
            try:
                response = requests.post(url, json={"prompt": workflow_json}, timeout=30)
                if response.ok:
                    result = response.json()
                    self._log(f"Workflow queued: prompt_id={result.get('prompt_id')}")
                    return {"ok": True, "prompt_id": result.get("prompt_id")}
                return {"ok": False, "status": response.status_code, "error": response.text}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        workflow_path = data.get("workflow_path")
        if not workflow_path or not os.path.exists(workflow_path):
            return {"ok": False, "error": f"workflow file not found: {workflow_path}"}

        import json
        try:
            with open(workflow_path, "r") as f:
                workflow = json.load(f)
            response = requests.post(url, json={"prompt": workflow}, timeout=30)
            if response.ok:
                result = response.json()
                self._log(f"Workflow queued: {workflow_path} → prompt_id={result.get('prompt_id')}")
                return {"ok": True, "prompt_id": result.get("prompt_id"), "workflow": workflow_path}
            return {"ok": False, "status": response.status_code, "error": response.text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def verify(self) -> bool:
        return self._find_comfyui_path() is not None

    def rollback(self) -> bool:
        return self._stop_server({}).get("ok", False)

    def health(self) -> Dict[str, Any]:
        if self._server_process is None:
            return {"ok": True, "message": "ComfyUI server stopped (idle)"}
        if self._server_process.poll() is not None:
            return {"ok": False, "message": "ComfyUI server process died"}
        return {"ok": True, "message": f"ComfyUI running: {self._server_url}"}