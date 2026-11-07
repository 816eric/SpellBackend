import os
import base64
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(name="client", scope="module")
def client_fixture(tmp_path_factory):
    """App on a throwaway database with admin credentials configured. One app
    per module: the models register on a global metadata, so the app can't be
    re-imported per test."""
    tmp_path = tmp_path_factory.mktemp("app")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)
    (tmp_path / "database").mkdir()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    monkeypatch.setenv("RATE_LIMIT_DISABLED", "true")
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    repo = os.path.dirname(os.path.dirname(__file__))
    monkeypatch.syspath_prepend(repo)
    monkeypatch.setattr("config.settings.templates", os.path.join(repo, "templates"), raising=False)
    import src.db_session as dbs
    importlib.reload(dbs)
    import main
    importlib.reload(main)
    yield TestClient(main.app)
    monkeypatch.undo()


def _basic(u, p):
    return {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}


def test_dashboard_requires_admin(client):
    assert client.get("/admin/dashboard").status_code == 401
    assert client.get("/admin/dashboard.json").status_code == 401
    assert client.get("/admin/dashboard", headers=_basic("admin", "wrong")).status_code == 401


def test_heartbeat_requires_login_and_is_counted(client):
    assert client.post("/usage/heartbeat", json={"seconds": 30}).status_code == 401
    r = client.post("/users/", json={"name": "kid", "password": "pw1234"})
    token = r.json()["token"]
    assert r.json()["created_at"]
    auth = {"Authorization": f"Bearer {token}"}
    assert client.post("/usage/heartbeat", json={"seconds": 30}, headers=auth).status_code == 200
    assert client.post("/usage/heartbeat", json={"seconds": 45}, headers=auth).status_code == 200
    assert client.post("/usage/heartbeat", json={"seconds": 99999}, headers=auth).status_code == 422
    assert client.post("/usage/heartbeat", json={"seconds": -5}, headers=auth).status_code == 422

    page = client.get("/admin/dashboard", headers=_basic("admin", "s3cret"))
    assert page.status_code == 200
    assert "#1" in page.text and "KID" not in page.text  # pseudonymous by default
    named = client.get("/admin/dashboard?names=1&period=week", headers=_basic("admin", "s3cret"))
    assert "KID" in named.text
    data = client.get("/admin/dashboard.json", headers=_basic("admin", "s3cret")).json()
    assert data["overview"]["registered"] == 1
    assert data["per_user"][0]["today_min"] == 1  # 75 s rounds to 1 min
    assert "name" not in data["per_user"][0]

    # Deleting the account removes its usage rows.
    assert client.delete("/users/kid", headers=auth).status_code == 200
    data = client.get("/admin/dashboard.json", headers=_basic("admin", "s3cret")).json()
    assert data["overview"]["registered"] == 0 and data["overview"]["usage_tracked_since"] is None


def test_report_is_private_to_the_child(client):
    a = client.post("/users/", json={"name": "ra", "password": "pw1234"}).json()["token"]
    b = client.post("/users/", json={"name": "rb", "password": "pw1234"}).json()["token"]
    ha, hb = {"Authorization": f"Bearer {a}"}, {"Authorization": f"Bearer {b}"}
    assert client.get("/users/RA/report").status_code == 401
    assert client.get("/users/RA/report", headers=hb).status_code == 403
    r = client.get("/users/RA/report", headers=ha)
    assert r.status_code == 200 and r.json()["time"]["streak_days"] == 0
