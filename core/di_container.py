"""
Dependency Injection Container for MOKA AI
"""

class DIContainer:
    def __init__(self):
        self._services = {}
        self._singletons = {}

    def register(self, name, service, is_singleton=False):
        """Register a service with the container"""
        self._services[name] = {
            'service': service,
            'singleton': is_singleton
        }

    def get(self, name):
        """Get a service instance from the container"""
        if name not in self._services:
            raise Exception(f"Service {name} not registered")

        service_info = self._services[name]

        if service_info['singleton']:
            # Return singleton instance or create if not exists
            if name not in self._singletons:
                self._singletons[name] = service_info['service']()
            return self._singletons[name]
        else:
            # Return new instance
            return service_info['service']()

    def resolve(self, service_class, *args, **kwargs):
        """Resolve and instantiate a service"""
        return service_class(*args, **kwargs)