from datetime import datetime
from learning.software_profile_database import SoftwareProfileDatabase, SoftwareProfile

class SoftwareProfileEngine:
    def __init__(self, db=None, logger=None):
        self._db = db or SoftwareProfileDatabase()
        self._logger = logger
        self._log = logger.info if logger else lambda *a, **k: None

    def generate(self, software, runtimes, tool_availability=None):
        results = {}
        dp = self._build_desktop_profile(software)
        self._db.add_profile(dp)
        results["desktop-scan"] = dp

        rp = self._build_runtime_profile(runtimes)
        self._db.add_profile(rp)
        results["desktop-runtime"] = rp

        for cat in ("dev", "browser", "communication", "productivity", "media", "games"):
            cp = self._build_category_profile(cat, software, runtimes)
            self._db.add_profile(cp)
            results[f"category-{cat}"] = cp

        return results

    def _build_desktop_profile(self, software):
        score = 0.95 if any(s.get("source") == "path" for s in software.values()) else 0.8
        return SoftwareProfile(
            profile_id="desktop-scan",
            name="Desktop Environment Scan",
            description=f"{len(software)} software entries detected",
            usage_patterns=[f"{n} {s['version']}" for n, s in software.items()],
            confidence_score=score,
            last_accessed=datetime.now(),
            is_active=True,
        )

    def _build_runtime_profile(self, runtimes):
        return SoftwareProfile(
            profile_id="desktop-runtime",
            name="Desktop Runtime",
            description=f"{len(runtimes)} processes running at scan",
            usage_patterns=runtimes[:50],
            confidence_score=0.7,
            last_accessed=datetime.now(),
            is_active=True,
        )

    def _build_category_profile(self, category, software, runtimes):
        cat_sw = {n: s for n, s in software.items() if s.get("category") == category}
        running = [n for n, s in cat_sw.items() if n.upper() in runtimes]
        return SoftwareProfile(
            profile_id=f"category-{category}",
            name=f"{category.title()} Tools",
            description=f"{len(cat_sw)} {category} apps detected",
            usage_patterns=["running"] if running else [],
            confidence_score=0.8 if cat_sw else 0.3,
            last_accessed=datetime.now(),
            is_active=True,
        )