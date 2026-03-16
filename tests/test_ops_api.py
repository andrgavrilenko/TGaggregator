import tgaggerator.api.app as api_mod


def test_ops_status_without_tg_config(client, monkeypatch):
    monkeypatch.setattr(api_mod.settings, "tg_api_id", None, raising=False)
    monkeypatch.setattr(api_mod.settings, "tg_api_hash", None, raising=False)

    resp = client.get("/ops/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "env" in body
    assert body["env"]["tg_api_configured"] is False
    assert body["tg_authorized"] is False


def test_ops_init_db_endpoint(client, monkeypatch):
    monkeypatch.setattr(api_mod, "init_db", lambda: None)
    resp = client.post("/ops/init-db")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_start_requires_login(client, monkeypatch):
    monkeypatch.setattr(api_mod, "init_db", lambda: None)

    async def _fake_auth():
        return False, None

    monkeypatch.setattr(api_mod, "_tg_authorized_state", _fake_auth)
    monkeypatch.setattr(api_mod, "_sync_public_channels_impl", lambda: 0)
    monkeypatch.setattr(
        api_mod,
        "_ingest_public_impl",
        lambda limit_per_channel: {
            "channels_total": 0,
            "channels_processed": 0,
            "channels_failed": 0,
            "inserted": 0,
        },
    )

    resp = client.post("/ops/start", json={"bootstrap_limit": 200, "run_ingest_once": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["requires_login"] is True


def test_ops_start_success(client, monkeypatch):
    monkeypatch.setattr(api_mod, "init_db", lambda: None)

    async def _fake_auth():
        return True, None

    async def _fake_sync():
        return 3

    async def _fake_ingest(limit_per_channel):
        return {
            "channels_total": 3,
            "channels_processed": 3,
            "channels_failed": 0,
            "inserted": 10 if limit_per_channel else 2,
        }

    monkeypatch.setattr(api_mod, "_tg_authorized_state", _fake_auth)
    monkeypatch.setattr(api_mod, "_sync_channels_impl", _fake_sync)
    monkeypatch.setattr(api_mod, "_ingest_impl", _fake_ingest)

    resp = client.post("/ops/start", json={"bootstrap_limit": 200, "run_ingest_once": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["channels_synced"] == 3
    assert body["bootstrap"]["inserted"] == 10
    assert body["ingest_once"]["inserted"] == 2


def test_ops_public_add(client, monkeypatch):
    monkeypatch.setattr(
        api_mod,
        "_upsert_public_channel",
        lambda handle: {"id": 1, "tg_id": 123, "title": "X", "username": "chan", "last_msg_id": 0},
    )
    resp = client.post("/ops/public/add", json={"handle": "@chan"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ops_sync_channels_public_mode(client, monkeypatch):
    async def _fake_auth():
        return False, None

    monkeypatch.setattr(api_mod, "_tg_authorized_state", _fake_auth)
    monkeypatch.setattr(api_mod, "_sync_public_channels_impl", lambda: 2)
    resp = client.post("/ops/sync-channels")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "public"
    assert body["channels_synced"] == 2
