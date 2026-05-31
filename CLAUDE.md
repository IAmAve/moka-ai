# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Moka AI is a local Windows AI voice companion with adaptive learning — a fully local, offline AI layer that behaves as a disciplined female mentor with Tagalog-first communication. The system has two distinct surfaces: the **runtime** (full app) and the **installer** (setup wizard).

## Current Branch: `merge-phases`

All phases are consolidated on this single branch. No branch-switching needed.

## Essential Commands

### Running the Application
```powershell
# Full application (runtime)
python moka.py

# Installer in development mode
python installer_wizard/main.py
```

### Testing
```powershell
# Run all tests with verbose output
pytest tests/ -v

# Run tests for a specific module
pytest tests/test_<module_name>.py -v

# Run a single test function
pytest tests/test_service_manager.py::TestServiceManager::test_register_service -v

# Run tests with keyword filtering (useful for finding related tests)
pytest tests/ -v -k "voice"     # All voice-related tests
pytest tests/ -v -k "test_mood" # Mood-related tests

# Run tests with coverage report
pytest tests/ --cov=core --cov-report=html --cov-report=term-missing

# Run tests in watch mode (useful during development)
pytest tests/ -v --watch

# Run specific test categories
pytest tests/ -v -k "learning"     # Learning system tests
pytest tests/ -v -k "memory"       # Memory system tests
pytest tests/ -v -k "safety"       # Safety/Emergency stop tests
```

### Code Quality & Linting
```powershell
# Install Ruff linter (one-time)
pip install ruff

# Check for linting issues
ruff check .

# Automatically fix fixable linting issues
ruff check . --fix

# Verify Python syntax for a specific module
python -m py_compile <module_path>

# Check for unused variables/imports
ruff check . --select F401,F841
```

### Building the Installer
```powershell
# Navigate to installer directory and build
cd installer
python build.py

# Output: dist/MokaAI-Setup/MokaAI-Setup.exe

# For development testing of installer
python installer_wizard/main.py
```

### Debugging & Diagnostics
```powershell
# Enable verbose logging via environment variable
set LOG_LEVEL=DEBUG
python moka.py

# Check service status at runtime (requires running application)
# Services can be inspected via ServiceManager.get_service_status(name) or Socket.IO events

# Validate Python environment
python -c "import sys; print(f'Python {sys.version}')"

# Check installed packages
pip list

# Monitor EventBus events (debugging)
# Add temporary subscribers in code to monitor specific event types
```

### Dependency Management
```powershell
# Install/update dependencies from requirements.txt
pip install -r requirements.txt

# Upgrade specific package
pip install --upgrade <package_name>

# Generate requirements.txt from current environment
pip freeze > requirements.txt
```

## Architecture Overview

### Core Services Layer (`core/`)
All services follow a standardized lifecycle managed by `ServiceManager`:
- Registration → Start → Operation → Stop (in reverse dependency order)
- Key services: `EventBus`, `ServiceManager`, `DIContainer`, `HealthMonitor`, `VersionManager`, `EnvironmentManager`, `Telemetry`

### Phase Services (`core/services.py`)
Wrappers that connect `ServiceManager` lifecycle to modular phases:
- **Phase 1**: `Phase1OrchestratorService` → Task orchestration pipeline (Intent → Plan → Route → Execute → Learn)
- **Phase 2**: `PersonalityService` → Mentor persona + mood modulation (Tagalog-first)
- **Phase 3**: `VoiceService` → Voice activation, STT/TTS processing
- **Phase 4**: `MemoryService` → Short-term, long-term, and behavior memory systems
- **Phase 5**: `LearningService` → Adaptive learning (observe → draft → test → approval → skill)
- **Phase 6**: `SafetyService` → Emergency stop (starts first, stops last)
- **Phase 12**: `Phase12ModuleRegistryService` → Tracks registered modules for plugin system
- **Phase 13**: `Phase13MigrationManagerService` → Handles database/config migrations

### Communication Pattern
All inter-service communication occurs exclusively through `EventBus`:
```python
# Publishing events
event_bus.publish("event_type", {"key": "value"})

# Subscribing to events
callback = lambda data: handle_event(data)
event_bus.subscribe("event_type", callback)
```

Key system events: `moka:startup_validated`, `moka:services_started`, `moka:shutdown_initiated`, `moka:shutdown_complete`, `workflow.stage.completed`, `memory_update`, `skill_update`, `learning:approval_required`, `hermes:approval_required`, `safety:trigger`

### Memory System (`memory/`)
Three-tier architecture:
- **ShortTermMemory**: Current session context (rolling window)
- **LongTermMemory**: Personality-backed episodic storage, queryable
- **BehaviorMemory**: Pattern-based storage for learning system

### Plugin System (`plugins/`)
Plugins are loaded at startup via `PluginManager.initialize()`:
- Lifecycle: `load()` → `initialize()` → `start()`
- Services self-register with `ServiceManager`
- Communication via `EventBus` only (no direct plugin-to-plugin calls)

### Installer Architecture
Two UI layers sharing core business logic:
- **Legacy**: `installer/wizard.py` (Dear PyGUI)
- **Current**: `installer_wizard/` (PyWebView2 with HTML/JS/CSS)

Core business logic (`installer/core/`):
- `hardware.py`: GPU/VRAM detection with vendor-specific corrections
- `models.py`: Model recommendation based on tiers.yaml
- `deps.py`: Dependency resolution and installation
- `downloader.py`: Model acquisition (GitHub, HuggingFace, Ollama)
- `writer.py`: Configuration generation via Jinja2 templates
- `shortcuts.py`: Windows shortcut creation and auto-start task scheduling

## Development Workflow

### Typical Implementation Steps
1. **Understand the architecture**: Review relevant service wrappers in `core/services.py`
2. **Identify extension points**: Look for appropriate EventBus events to subscribe/publish
3. **Implement functionality**: Follow existing patterns in similar phase services
4. **Add tests**: Create unit tests in `tests/` directory following existing patterns
5. **Validate**: Run full test suite and manual verification

### Service Creation Guidelines
When adding new functionality:
1. Create a service wrapper in `core/services.py` inheriting from base service pattern
2. Implement standard lifecycle methods: `start()`, `stop()`, `get_status()`
3. Register with `ServiceManager` in `moka.py` during initialization (in `_init_phase_2_7()` or similar)
4. Communicate via `EventBus` - avoid direct service-to-service calls
5. Follow shutdown order dependencies (safety first/last, others in reverse dependency order)
6. Add persistence handling in `stop()` methods where appropriate (see existing services for examples)

### Testing Patterns
- **Unit tests**: Mock external dependencies (hardware, network, filesystems)
- **Integration tests**: Verify service interactions through EventBus
- **Voice tests**: Mock audio input/output devices using libraries like `unittest.mock`
- **EventBus testing**: Use actual EventBus instance in tests to verify publish/subscribe behavior
- **Persistence testing**: Test that `stop()` methods properly save state when applicable
- **Always run**: `pytest tests/ -v` before submitting changes

### Common Development Tasks
- **Adding a new EventBus event**: 
  1. Define the event name following the pattern `domain:action` (e.g., `feature:event`)
  2. Publish in the service where the event originates
  3. Subscribe in services that need to react to the event
  4. Add tests for both publishing and subscribing behavior

- **Adding persistence to a service**:
  1. In `start()`: Ensure data directory exists (`self._data_dir.mkdir(exist_ok=True)`)
  2. In `stop()`: Save relevant state to files in the data directory
  3. In constructor/start: Load existing state if available
  4. Handle exceptions gracefully with logging

- **Working with the Plugin System**:
  1. Plugins go in the `plugins/` directory
  2. Each plugin should have an `__init__.py` and follow the lifecycle pattern
  3. Plugins auto-register with ServiceManager via `PluginManager`
  4. Plugins communicate exclusively through EventBus

## Common Troubleshooting

### Runtime Issues
- **Port 5000 conflicts**: Change port in `config.yaml` or stop conflicting service
- **Audio device issues**: Verify microphone/speaker configuration in Windows Sound settings
- **Import errors**: Ensure dependencies installed via `pip install -r requirements.txt`
- **Model loading failures**: Check internet connection and available disk space
- **EventBus not working**: Verify services are properly started and subscribed
- **Service not starting**: Check that service is registered with ServiceManager before `start()` is called

### Build/Installer Issues
- **Missing dependencies**: Verify `installer/core/` modules have required packages
- **Shortcut creation failures**: Run installer scripts with appropriate privileges
- **Model download interruptions**: Resume downloads by re-running build process
- **PyWebView2 issues**: Ensure webview package is installed and compatible with Python version

### Debugging Aids
- **Log files**: Check application directory for timestamped log files
- **Socket.IO monitoring**: Use browser dev tools to monitor frontend-backend communication (for installer_wizard)
- **Service introspection**: Use `ServiceManager.get_service_status(name)` during runtime
- **EventBus debugging**: Add temporary logging to event handlers to trace event flow
- **Data persistence**: Check `data/` directory for saved state files from services

## Project Files

- **TASK_COMPLETION_SUMMARY.md**: Tracks implementation progress across all phases — useful for understanding what's been built and what verification tasks remain.
- **scripts/**: Reserved for automation scripts (currently empty).