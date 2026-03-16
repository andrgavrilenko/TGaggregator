from importlib import reload

from fastapi.testclient import TestClient


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


def test_channels_batch_patch(tmp_path, monkeypatch):
    db_path = tmp_path / "test_api_batch.db"
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
        c1 = repo_mod.upsert_channel(db, tg_id=1001, title="Chan1", username=None, is_private=True)
        c2 = repo_mod.upsert_channel(db, tg_id=1002, title="Chan2", username=None, is_private=True)
        db.commit()
        ids = [c1.id, c2.id]

    local_client = TestClient(api_mod.app)
    resp = local_client.patch("/channels", json={"channel_ids": ids, "muted": True})
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 2
    assert all(item["muted"] is True for item in payload)
