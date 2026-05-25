"""
Debug Loop — auto-fix with iteration cap and manual fallback.

auto_fix() retries a code-fixing handler up to max_attempts.
If all attempts fail, marks as "exhausted" → human escalation.
Each attempt modifies code in the sandbox worktree and commits.
"""

from typing import Callable, Dict, Any


class DebugLoop:
    def __init__(self, max_attempts: int = 3, logger=None):
        self.max_attempts = max_attempts
        self._logger = logger
        self._log = logger.info if logger else lambda m: None

    def should_escalate(self, attempt_count: int) -> bool:
        return attempt_count >= self.max_attempts

    def auto_fix(
        self,
        sandbox_id: str,
        code_handler: Callable[[], bool],
        max_attempts: int = None,
    ) -> Dict[str, Any]:
        max_attempts = max_attempts or self.max_attempts
        for attempt in range(1, max_attempts + 1):
            self._log(f"Debug attempt {attempt}/{max_attempts} for sandbox {sandbox_id}")
            try:
                success = code_handler()
                if success:
                    self._log(f"Fix succeeded on attempt {attempt}")
                    return {"success": True, "exhausted": False, "attempts": attempt}
            except Exception as e:
                self._log(f"Attempt {attempt} failed with: {e}")

        self._log(f"All {max_attempts} attempts exhausted for sandbox {sandbox_id}")
        return {"success": False, "exhausted": True, "attempts": max_attempts}