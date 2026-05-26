"""ImageMonitor - WebSocket + polling fallback for ComfyUI generation progress."""

from __future__ import annotations
import threading
import time
from typing import Any, Dict, Optional

from core.event_bus import EventBus


class ImageMonitor:
    def __init__(self, comfyui_url: str = "http://localhost:8188", logger=None):
        self._comfyui_url = comfyui_url
        self._ws_url = comfyui_url.replace("http", "ws") + "/ws"
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._subscriptions: Dict[str, str] = {}  # prompt_id -> request_id
        self._status: Dict[str, Dict[str, Any]] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._event_bus = None
        try:
            import websockets
            self._websockets_available = True
        except ImportError:
            self._websockets_available = False
            self._log("websockets not available - using polling fallback")

    def set_event_bus(self, event_bus: EventBus):
        self._event_bus = event_bus

    def subscribe(self, prompt_id: str, request_id: str):
        self._subscriptions[prompt_id] = request_id
        self._status[prompt_id] = {"state": "running", "progress": 0, "output": None}
        self._stop_events[prompt_id] = threading.Event()
        if self._websockets_available:
            t = threading.Thread(target=self._ws_loop, args=(prompt_id,), daemon=True)
            t.start()
        else:
            t = threading.Thread(target=self._poll_loop, args=(prompt_id,), daemon=True)
            t.start()

    def unsubscribe(self, prompt_id: str):
        if prompt_id in self._stop_events:
            self._stop_events[prompt_id].set()
        self._subscriptions.pop(prompt_id, None)
        self._status.pop(prompt_id, None)

    def get_status(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        return self._status.get(prompt_id)

    def _ws_loop(self, prompt_id: str):
        import asyncio, websockets, json as jsonmod
        stop = self._stop_events.get(prompt_id)
        while stop and not stop.is_set():
            try:
                async def receive():
                    async with websockets.connect(self._ws_url) as ws:
                        while stop and not stop.is_set():
                            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            self._handle_ws_message(prompt_id, jsonmod.loads(msg))
                asyncio.run(receive())
            except Exception as e:
                self._log(f"WS error for {prompt_id}: {e}, retrying in 5s")
                time.sleep(5)

    def _poll_loop(self, prompt_id: str):
        import requests
        stop = self._stop_events.get(prompt_id)
        while stop and not stop.is_set():
            try:
                r = requests.get(f"{self._comfyui_url}/history/{prompt_id}", timeout=10)
                if r.ok:
                    data = r.json()
                    if prompt_id in data:
                        self._status[prompt_id] = {"state": "completed", "output": data[prompt_id].get("outputs", {})}
                        self._publish("image_gen.finished", {"prompt_id": prompt_id})
                        return
            except Exception as e:
                self._log(f"Polling error for {prompt_id}: {e}")
            time.sleep(5)

    def _handle_ws_message(self, prompt_id: str, msg: dict):
        msg_type = msg.get("type", "")
        data = msg.get("data", {})

        if msg_type == "progress":
            self._status[prompt_id] = {"state": "running", "progress": data.get("value", 0), "node": data.get("node", "")}
            self._publish("image_gen.progress", {"prompt_id": prompt_id, "progress": data.get("value", 0), "node": data.get("node", "")})
        elif msg_type == "executing":
            self._publish("image_gen.executing", {"prompt_id": prompt_id, "node": data.get("node", "")})
        elif msg_type == "finished":
            self._status[prompt_id] = {"state": "completed", "output": data.get("output", {})}
            req_id = self._subscriptions.get(prompt_id)
            self._publish("image_gen.finished", {"prompt_id": prompt_id, "request_id": req_id, "output": data.get("output", {})})
            self.unsubscribe(prompt_id)
        elif msg_type == "error":
            self._status[prompt_id] = {"state": "failed", "error": data.get("error", "")}
            self._publish("image_gen.error", {"prompt_id": prompt_id, "error": data.get("error", "")})
            self.unsubscribe(prompt_id)

    def _publish(self, event: str, data: dict):
        if self._event_bus:
            self._event_bus.publish(event, data)