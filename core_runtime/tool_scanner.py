"""Tool Scanner - maps executable names to Moka plugin names."""

class ToolScanner:
    TOOL_TO_PLUGIN = {
        "code":           "vscode",
        "git":            "git",
        "chrome":         "chrome",
        "firefox":        "chrome",
        "msedge":         "chrome",
        "explorer":       "explorer",
        "wt":             "terminal",
        "cmd":            "terminal",
        "python":         "terminal",
        "python3":        "terminal",
        "node":           "terminal",
        "npm":            "terminal",
        "docker":         "terminal",
        "docker-compose": "terminal",
        "go":             "terminal",
        "rustc":          "terminal",
        "make":           "terminal",
        "ssh":            "terminal",
        "kubectl":        "terminal",
        "terraform":      "terminal",
        "comfyui":        "comfyui",
    }

    def map(self, exe_name: str) -> str | None:
        return self.TOOL_TO_PLUGIN.get(exe_name.lower())

    def bulk_map(self, exe_names: list[str]) -> list[str]:
        return [self.TOOL_TO_PLUGIN[n.lower()] for n in exe_names if n.lower() in self.TOOL_TO_PLUGIN]