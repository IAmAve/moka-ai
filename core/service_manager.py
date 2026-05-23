"""
Service Manager for MOKA AI
"""

from enum import Enum
from typing import Any, Dict, List, Optional

class ServiceStatus(Enum):
    UNKNOWN = "unknown"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"

class ServiceManager:
    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register_service(self, name: str, service: Any) -> None:
        """Register a service with the manager."""
        self._services[name] = {
            'service': service,
            'status': ServiceStatus.STOPPED
        }

    def get_service(self, name: str) -> Optional[Any]:
        """Get a service instance by name."""
        entry = self._services.get(name)
        return entry['service'] if entry else None

    def start_service(self, name: str) -> bool:
        """Start a registered service."""
        entry = self._services.get(name)
        if not entry:
            return False
        if entry['status'] == ServiceStatus.RUNNING:
            return True
        try:
            svc = entry['service']
            if hasattr(svc, 'start'):
                svc.start()
            entry['status'] = ServiceStatus.RUNNING
            return True
        except Exception:
            entry['status'] = ServiceStatus.FAILED
            return False

    def stop_service(self, name: str) -> bool:
        """Stop a running service."""
        entry = self._services.get(name)
        if not entry:
            return False
        if entry['status'] == ServiceStatus.STOPPED:
            return True
        try:
            svc = entry['service']
            if hasattr(svc, 'stop'):
                svc.stop()
            entry['status'] = ServiceStatus.STOPPED
            return True
        except Exception:
            entry['status'] = ServiceStatus.FAILED
            return False

    def get_status(self, name: str) -> ServiceStatus:
        """Get the status of a service."""
        entry = self._services.get(name)
        return entry['status'] if entry else ServiceStatus.UNKNOWN

    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self._services.keys())