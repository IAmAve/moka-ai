# MOKA AI - Main Application Entry Point
__version__ = "0.1.0"

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
from core_runtime.image_runtime_manager import ImageRuntimeManager
from core.services import (
    Phase1OrchestratorService, PersonalityService, VoiceService,
    MemoryService, LearningService, SafetyService,
    Phase12ModuleRegistryService, Phase13MigrationManagerService,
)

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
        self.image_runtime = ImageRuntimeManager(
            cache=self.desktop_runtime.get_cache() if self.desktop_runtime else None,
            event_bus=self.event_bus,
            logger=self.logger,
        )
        self.workers = {}
        self.initialized = False
        # New modules wired at construction time
        self.env_manager = EnvironmentManager()
        self.version_manager = VersionManager()
        self.health_monitor = HealthMonitor(self.event_bus)
        self.telemetry = Telemetry()

        # Phase 1 — TaskOrchestrator (standalone)
        self.phase1_orchestrator = Phase1OrchestratorService(
            event_bus=self.event_bus, logger=self.logger
        )
        # Phase 2-7 Service wrappers
        self.personality_service = PersonalityService(
            event_bus=self.event_bus, logger=self.logger
        )
        self.voice_service = VoiceService(
            event_bus=self.event_bus, logger=self.logger
        )
        self.memory_service = MemoryService(
            event_bus=self.event_bus, logger=self.logger
        )
        self.learning_service = LearningService(
            event_bus=self.event_bus, logger=self.logger
        )
        self.safety_service = SafetyService(
            event_bus=self.event_bus, logger=self.logger
        )
        # Phase 12 — Module Registry
        self.phase12_module_registry = Phase12ModuleRegistryService(
            event_bus=self.event_bus, logger=self.logger
        )
        # Phase 13 — Migration Manager
        self.phase13_migration_manager = Phase13MigrationManagerService(
            event_bus=self.event_bus, logger=self.logger
        )

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

        # 6. Phase 1-7 service initialization + software profile bridge
        self._init_phase_2_7()

        # 7. Register core services
        self._register_core_services()

        # 8. Startup validation
        if not self._validate_startup():
            raise RuntimeError("Startup validation failed")

        # 9. Start all services
        self._start_services()

        # 10. Start health monitoring
        self.health_monitor.start()

        # Phase 13: run pending migrations at startup
        try:
            self.phase13_migration_manager.migration_manager.migrate()
        except Exception as e:
            self.logger.warning(f"Migration run incomplete: {e}")

        self.logger.info("MOKA AI initialized successfully")
        self.initialized = True

    def _init_desktop_runtime(self):
        result = self.desktop_runtime.run()
        self.logger.info(
            f"Desktop scan: {result['software_detected']} apps, "
            f"{result['runtime_count']} processes, "
            f"{result['profiles_generated']} profiles"
        )
        # Seed software profiles into Hermes for Phase 5 learning
        profiles = self.desktop_runtime.get_software_profiles() if self.desktop_runtime else []
        self.learning_service.seed_software_profiles(profiles)

    def _init_phase_2_7(self):
        # DI container registration
        self.dIContainer.register("phase1_orchestrator", lambda: self.phase1_orchestrator)
        self.dIContainer.register("personality_service", lambda: self.personality_service)
        self.dIContainer.register("voice_service", lambda: self.voice_service)
        self.dIContainer.register("memory_service", lambda: self.memory_service)
        self.dIContainer.register("learning_service", lambda: self.learning_service)
        self.dIContainer.register("safety_service", lambda: self.safety_service)
        self.dIContainer.register("phase12_module_registry", lambda: self.phase12_module_registry)
        self.dIContainer.register("phase13_migration_manager", lambda: self.phase13_migration_manager)

        # ServiceManager registration for start()/stop() lifecycle
        self.service_manager.register_service("phase1_orchestrator", self.phase1_orchestrator)
        self.service_manager.register_service("personality_service", self.personality_service)
        self.service_manager.register_service("voice_service", self.voice_service)
        self.service_manager.register_service("memory_service", self.memory_service)
        self.service_manager.register_service("learning_service", self.learning_service)
        self.service_manager.register_service("safety_service", self.safety_service)
        self.service_manager.register_service("phase12_module_registry", self.phase12_module_registry)
        self.service_manager.register_service("phase13_migration_manager", self.phase13_migration_manager)

    def _register_core_services(self):
        self.service_manager.register_service("health_monitor", self.health_monitor)
        self.service_manager.register_service("telemetry", self.telemetry)
        self.service_manager.register_service("version_manager", self.version_manager)
        self.service_manager.register_service("engineering_workflow_orchestrator", self.engineering_workflow)
        self.service_manager.register_service("image_runtime_manager", self.image_runtime)

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
            ("image_runtime", lambda: self.image_runtime),
            ("engineering_workflow", lambda: self.engineering_workflow),
            ("phase1_orchestrator", lambda: self.phase1_orchestrator),
            ("personality_service", lambda: self.personality_service),
            ("voice_service", lambda: self.voice_service),
            ("memory_service", lambda: self.memory_service),
            ("learning_service", lambda: self.learning_service),
            ("safety_service", lambda: self.safety_service),
            ("phase12_module_registry", lambda: self.phase12_module_registry),
            ("phase13_migration_manager", lambda: self.phase13_migration_manager),
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
        for name in list(self.service_manager.list_services()):
            self.service_manager.stop_service(name)
        # Phase 1-7 graceful shutdown (in reverse dependency order)
        if hasattr(self, 'safety_service'):
            self.safety_service.stop()
        if hasattr(self, 'phase13_migration_manager'):
            self.phase13_migration_manager.stop()
        if hasattr(self, 'phase12_module_registry'):
            self.phase12_module_registry.stop()
        if hasattr(self, 'learning_service'):
            self.learning_service.stop()
        if hasattr(self, 'memory_service'):
            self.memory_service.stop()
        if hasattr(self, 'voice_service'):
            self.voice_service.stop()
        if hasattr(self, 'personality_service'):
            self.personality_service.stop()
        if hasattr(self, 'phase1_orchestrator'):
            self.phase1_orchestrator.stop()
        if hasattr(self.telemetry, 'flush'):
            self.telemetry.flush()
        self.event_bus.publish("moka:shutdown_complete", {})
        self.logger.info("MOKA AI shutdown complete")
        self.initialized = False