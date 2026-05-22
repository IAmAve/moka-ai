"""
Plugin Manager for MOKA AI
"""

import os
import importlib.util

class PluginManager:
    def __init__(self, config):
        self.config = config
        self.plugins = {}
        self.plugin_directory = config.get("plugins_path", "plugins/")

    def initialize(self):
        """Initialize the plugin manager"""
        self.load_plugins()

    def load_plugins(self):
        """Load all plugins from the plugin directory"""
        if not os.path.exists(self.plugin_directory):
            return

        for filename in os.listdir(self.plugin_directory):
            if filename.endswith(".py"):
                self.load_plugin(filename)

    def load_plugin(self, plugin_file):
        """Load a specific plugin"""
        try:
            spec = importlib.util.spec_from_file_location(
                "plugin",
                os.path.join(self.plugin_directory, plugin_file)
            )
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)

            # Add plugin to loaded plugins
            plugin_name = os.path.splitext(plugin_file)[0]
            self.plugins[plugin_name] = plugin_module

        except Exception as e:
            print(f"Error loading plugin {plugin_file}: {e}")

    def get_plugin(self, name):
        """Get a loaded plugin by name"""
        return self.plugins.get(name)

    def list_plugins(self):
        """List all loaded plugins"""
        return list(self.plugins.keys())

    def execute_plugin(self, plugin_name, data):
        """Execute a plugin with provided data"""
        plugin = self.plugins.get(plugin_name)
        if plugin and hasattr(plugin, 'execute'):
            return plugin.execute(data)
        return None