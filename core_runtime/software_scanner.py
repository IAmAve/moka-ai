import os, shutil
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

class SoftwareScanner:
    KNOWN_SOFTWARE = {
        # dev
        "python": {"category": "dev", "exe": "python"},
        "node": {"category": "dev", "exe": "node"},
        "git": {"category": "dev", "exe": "git"},
        "docker": {"category": "dev", "exe": "docker"},
        "code": {"category": "dev", "exe": "code"},
        "devenv": {"category": "dev", "exe": "devenv"},
        "pycharm64": {"category": "dev", "exe": "pycharm64"},
        "idea64": {"category": "dev", "exe": "idea64"},
        "rustc": {"category": "dev", "exe": "rustc"},
        "go": {"category": "dev", "exe": "go"},
        "java": {"category": "dev", "exe": "java"},
        "mvn": {"category": "dev", "exe": "mvn"},
        "gradle": {"category": "dev", "exe": "gradle"},
        "cmake": {"category": "dev", "exe": "cmake"},
        "make": {"category": "dev", "exe": "make"},
        # browsers
        "chrome": {"category": "browser", "exe": "chrome"},
        "firefox": {"category": "browser", "exe": "firefox"},
        "msedge": {"category": "browser", "exe": "msedge"},
        "opera": {"category": "browser", "exe": "opera"},
        "brave": {"category": "browser", "exe": "brave"},
        # communication
        "slack": {"category": "communication", "exe": "slack"},
        "teams": {"category": "communication", "exe": "teams"},
        "discord": {"category": "communication", "exe": "discord"},
        "zoom": {"category": "communication", "exe": "zoom"},
        "outlook": {"category": "communication", "exe": "OUTLOOK"},
        # productivity
        "notion": {"category": "productivity", "exe": "Notion"},
        "obsidian": {"category": "productivity", "exe": "Obsidian"},
        "onenote": {"category": "productivity", "exe": "ONENOTE"},
        "dropbox": {"category": "productivity", "exe": "Dropbox"},
        "onedrive": {"category": "productivity", "exe": "OneDrive"},
        "libreoffice": {"category": "productivity", "exe": "soffice"},
        # media
        "spotify": {"category": "media", "exe": "Spotify"},
        "vlc": {"category": "media", "exe": "vlc"},
        "gimp": {"category": "media", "exe": "gimp"},
        "blender": {"category": "media", "exe": "blender"},
        # games
        "steam": {"category": "games", "exe": "steam"},
        "epic": {"category": "games", "exe": "EpicGamesLauncher"},
        "minecraft": {"category": "games", "exe": "MinecraftLauncher"},
    }

    def scan(self):
        results = {}
        results.update(self._scan_via_path())
        if HAS_WINREG:
            results.update(self._scan_via_registry())
        return results

    def _scan_via_path(self):
        found = {}
        for name, spec in self.KNOWN_SOFTWARE.items():
            path = shutil.which(spec["exe"])
            if path:
                version = self._get_version(path) or "unknown"
                found[name] = {"name": name, "version": version, "path": path,
                               "source": "path", "category": spec["category"]}
        return found

    def _scan_via_registry(self):
        found = {}
        hives = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, base in hives:
            found.update(self._search_hive(hive, base))
        return found

    def _search_hive(self, hive, base_key):
        results = {}
        try:
            with winreg.OpenKey(hive, base_key, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i)
                        i += 1
                        dn = self._read_val(hive, f"{base_key}\\{sub}", "DisplayName")
                        if not dn:
                            continue
                        ver = self._read_val(hive, f"{base_key}\\{sub}", "DisplayVersion")
                        loc = self._read_val(hive, f"{base_key}\\{sub}", "InstallLocation")
                        for name, spec in self.KNOWN_SOFTWARE.items():
                            if name not in results and (name.lower() in dn.lower() or spec["exe"].lower() in dn.lower()):
                                results[name] = {"name": name, "version": ver or "unknown",
                                                "path": loc or "", "source": "registry",
                                                "category": spec["category"]}
                    except OSError:
                        break
        except OSError:
            pass
        return results

    def _read_val(self, hive, path, name):
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as k:
                return winreg.QueryValueEx(k, name)[0]
        except OSError:
            return None

    def _get_version(self, path):
        try:
            import subprocess
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                return r.stdout.splitlines()[0].strip()[:64]
        except Exception:
            pass
        return None