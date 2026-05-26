import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import app, socketio, AGENT_STATE


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"<!DOCTYPE" in r.data or b"<html" in r.data


def test_agent_state_has_required_keys(client):
    required = {"status", "transcript", "last_message"}
    assert required.issubset(AGENT_STATE.keys())


def test_connect_emit_agent_state(client):
    from backend.app import socketio
    tc = socketio.test_client(app)
    received = tc.get_received()
    agent_events = [e for e in received if e["name"] == "agent_state"]
    assert len(agent_events) == 1
    assert agent_events[0]["args"][0]["status"] == "idle"
    tc.disconnect()