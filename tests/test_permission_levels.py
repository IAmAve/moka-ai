# tests/test_permission_levels.py
import tempfile
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from safety.permission_levels import PermissionManager, PermissionLevel


def test_config_hot_reload():
    """Test that PermissionManager can hot-reload configuration from disk."""
    temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump({"approval_timeout_seconds": 30}, temp_config)
    temp_config.close()

    try:
        manager = PermissionManager(config_path=temp_config.name)
        assert manager.get_approval_timeout() == 30, f"Expected 30, got {manager.get_approval_timeout()}"

        # Modify file externally
        with open(temp_config.name, 'w') as f:
            json.dump({"approval_timeout_seconds": 45}, f)

        manager.reload()
        assert manager.get_approval_timeout() == 45, f"Expected 45 after reload, got {manager.get_approval_timeout()}"
    finally:
        os.unlink(temp_config.name)


def test_default_config():
    """Test PermissionManager returns default config when file doesn't exist."""
    manager = PermissionManager(config_path="nonexistent_config.json")
    assert manager.get_approval_timeout() == 60


def test_get_level_for_action():
    """Test action to permission level mapping."""
    manager = PermissionManager()
    assert manager.get_level_for_action("read") == PermissionLevel.SAFE
    assert manager.get_level_for_action("delete") == PermissionLevel.DANGEROUS
    assert manager.get_level_for_action("unknown") == PermissionLevel.MEDIUM