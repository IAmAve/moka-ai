# MOKA AI - Main Application Entry Point

from config import Config
from logger import Logger
from core.di_container import DIContainer
from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.service_manager import ServiceManager, ServiceStatus
from core.health_monitor import HealthMonitor
from core.version_manager import VersionManager
from core.environment_manager import EnvironmentManager
from core.telemetry import Telemetry
from core_runtime.desktop_runtime_manager import DesktopRuntimeManager
from core_runtime.engineering_workflow_orchestrator import EngineeringWorkflowOrchestrator

class MokaAI:
    def __init__(self):
        self.config = Config()
        self.logger = Logger()
        self.event_bus = EventBus()
        self.service_manager = ServiceManager()
        self.dIContainer = DIContainer()
        self.plugin_manager = None
        self.desktop_runtime = DesktopRuntimeManager(logger=self.logger)
        self.engineering_workflow = EngineeringWorkflowOrchestrator(
            event_bus=self.event_bus,
            service_manager=self.service_manager,
            logger=self.logger,
        )
        self.workers = {}
        self.initialized = False
        # New modules wired at construction time
        self.env_manager = EnvironmentManager()
        self.version_manager = VersionManager()
        self.health_monitor = HealthMonitor(self.event_bus)
        self.telemetry = Telemetry()

    def initialize(self):
        # 1. Environment validation
        if not self.env_manager.validate():
            raise RuntimeError("Environment validation failed: " + "; ".join(self.env_manager.get_errors()))

        # 2. Load configuration
        self.config.load()
        self.logger.initialize(self.config.get("log_level", "INFO"))
        self.logger.info("MOKA AI starting up...")

        # 3. Register core services with DI
        self.dIContainer.register("event_bus", lambda: self.event_bus)
        self.dIContainer.register("telemetry", lambda: self.telemetry, is_singleton=True)

        # 4. Setup plugin system
        self._init_plugins()

        # 5. Desktop runtime scan
        self._init_desktop_runtime()

        # 6. Register core services
        self._register_core_services()

        # 7. Startup validation
        if not self._validate_startup():
            raise RuntimeError("Startup validation failed")

        # 8. Start all services
        self._start_services()

        # 9. Start health monitoring
        self.health_monitor.start()

        self.logger.info("MOKA AI initialized successfully")
        self.initialized = True

    def _init_desktop_runtime(self):
        result = self.desktop_runtime.run()
        self.logger.info(
            f"Desktop scan: {result['software_detected']} apps, "
            f"{result['runtime_count']} processes, "
            f"{result['profiles_generated']} profiles"
        )

    def _register_core_services(self):
        self.service_manager.register_service("health_monitor", self.health_monitor)
        self.service_manager.register_service("telemetry", self.telemetry)
        self.service_manager.register_service("version_manager", self.version_manager)
        self.service_manager.register_service("engineering_workflow_orchestrator", self.engineering_workflow)

    def _init_plugins(self):
        self.plugin_manager = PluginManager(self.config)
        self.plugin_manager.initialize()
        self.service_manager.register_service("plugin_manager", self.plugin_manager)

    def _validate_startup(self) -> bool:
        checks = [
            ("config", lambda: self.config.config),
            ("logger", lambda: self.logger),
            ("event_bus", lambda: self.event_bus),
            ("service_manager", lambda: self.service_manager),
            ("health_monitor", lambda: self.health_monitor),
            ("version_manager", lambda: self.version_manager),
            ("env_manager", lambda: self.env_manager),
            ("desktop_runtime", lambda: self.desktop_runtime),
            ("engineering_workflow", lambda: self.engineering_workflow),
        ]
        for name, check_fn in checks:
            try:
                result = check_fn()
                if result is None:
                    self.logger.error(f"Startup check failed: {name} is None")
                    return False
            except Exception as e:
                self.logger.error(f"Startup check failed: {name} raised {e}")
                return False
        self.event_bus.publish("moka:startup_validated", {"status": "ok"})
        return True

    def _start_services(self):
        for name in self.service_manager.list_services():
            if self.service_manager.get_status(name) == ServiceStatus.STOPPED:
                self.service_manager.start_service(name)
        self.event_bus.publish("moka:services_started", {})

    def shutdown(self):
        self.logger.info("MOKA AI shutting down...")
        self.health_monitor.stop()
        if hasattr(self.engineering_workflow, 'stop'):
            self.engineering_workflow.stop()
        if hasattr(self.telemetry, 'flush'):
            self.telemetry.flush()
        for name in list(self.service_manager.list_services()):
            self.service_manager.stop_service(name)
        self.event_bus.publish("moka:shutdown_complete", {})
        self.logger.info("MOKA AI shutdown complete")
        self.initialized = False