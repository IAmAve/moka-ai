"""Runtime Scanner - snapshot of running processes via tasklist."""

import subprocess
import csv
import io

class RuntimeScanner:
    def scan(self) -> list[str]:
        try:
            r = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode != 0:
                return []
            names = []
            reader = csv.reader(io.StringIO(r.stdout))
            for row in reader:
                if row:
                    names.append(row[0].strip('"').upper())
            return list(dict.fromkeys(names))
        except Exception:
            return []