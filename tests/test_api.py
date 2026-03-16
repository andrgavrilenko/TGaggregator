from importlib import reload

from fastapi.testclient import TestClient

from tgaggerator.api.app import app


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_channels_patch(tmp_path, monkeypatch):
    db_path = tmp_path / "test_api.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")

    import tgaggerator.config as cfg
    import tgaggerator.db as db_mod
    import tgaggerator.init_db as init_mod
    import tgaggerator.repository as repo_mod
    import tgaggerator.api.app as api_mod

    reload(cfg)
    reload(db_mod)
    reload(init_mod)
    reload(repo_mod)
    reload(api_mod)

    init_mod.init_db_for_tests()
    with db_mod.SessionLocal() as db:
        repo_mod.upsert_channel(db, tg_id=777, title="API Chan", username=None, is_private=True)
        db.commit()

    local_client = TestClient(api_mod.app)

    channels = local_client.get("/channels")
    assert channels.status_code == 200
    payload = channels.json()
    assert len(payload) == 1
    channel_id = payload[0]["id"]

    resp = local_client.patch(f"/channels/{channel_id}", json={"enabled": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
