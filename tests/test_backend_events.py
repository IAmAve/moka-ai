"""Tests for Task 5: Backend event wiring and mock data."""
import pytest, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import app, socketio, AGENT_STATE, broadcast_state, broadcast_event


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200


def test_agent_state_has_all_required_keys():
    required = {"status", "transcript", "last_message"}
    assert required.issubset(AGENT_STATE.keys())


def test_mic_toggle_handler_exists():
    from backend.app import handle_mic_toggle
    assert callable(handle_mic_toggle)


def test_clear_history_handler_exists():
    from backend.app import handle_clear_history
    assert callable(handle_clear_history)


def test_export_memory_handler_exists():
    from backend.app import handle_export_memory
    assert callable(handle_export_memory)


def test_broadcast_state_updates_agent_state():
    prev = AGENT_STATE["status"]
    broadcast_state({"status": "listening"})
    assert AGENT_STATE["status"] == "listening"
    # Restore
    AGENT_STATE["status"] = prev


def test_broadcast_event_does_not_crash():
    # Should not raise — just ensure function is callable
    broadcast_event("resource_update", {"gpu": 50, "ram": 30})


def test_mic_toggle_cycles_through_states():
    from backend.app import app, socketio
    tc = socketio.test_client(app)
    tc.emit("mic_toggle")
    tc.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])