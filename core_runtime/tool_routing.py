"""
Tool Routing Module for MOKA AI Core Runtime

This module handles routing of tools and commands.
"""

from typing import Dict, Any, Callable, List
import importlib

class ToolRouter:
    """Routes tools and commands to appropriate handlers"""

    def __init__(self):
        self.tools = {}
        self.tool_callbacks = {}

    def register_tool(self, name: str, tool_function: Callable):
        """Register a tool with the router"""
        self.tools[name] = tool_function

    def route_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Route to appropriate tool"""
        if tool_name in self.tools:
            return self.tools[tool_name](*args, **kwargs)
        return None

    def get_tool(self, tool_name: str) -> Callable:
        """Get registered tool by name"""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self.tools.keys())

    def execute_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Execute a specific tool"""
        if tool_name in self.tools:
            return self.tools[tool_name](*args, **kwargs)
        return None