from datetime import UTC, datetime
from importlib import reload


def test_insert_message_dedup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")

    import tgaggerator.config as cfg
    import tgaggerator.db as db_mod
    import tgaggerator.init_db as init_mod
    import tgaggerator.repository as repo_mod

    reload(cfg)
    reload(db_mod)
    reload(init_mod)
    reload(repo_mod)

    init_mod.init_db_for_tests()

    with db_mod.SessionLocal() as db:
        channel = repo_mod.upsert_channel(db, tg_id=123, title="Test", username=None, is_private=True)
        db.commit()

        first = repo_mod.insert_message_if_new(
            db,
            channel_id=channel.id,
            tg_message_id=1,
            date_utc=datetime.now(UTC),
            text="hello",
            media_type=None,
            views=None,
            forwards=None,
            link=None,
            raw_json=None,
        )
        second = repo_mod.insert_message_if_new(
            db,
            channel_id=channel.id,
            tg_message_id=1,
            date_utc=datetime.now(UTC),
            text="hello2",
            media_type=None,
            views=None,
            forwards=None,
            link=None,
            raw_json=None,
        )
        db.commit()

    assert first is True
    assert second is False


def test_set_channel_flags(tmp_path, monkeypatch):
    db_path = tmp_path / "test_flags.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")

    import tgaggerator.config as cfg
    import tgaggerator.db as db_mod
    import tgaggerator.init_db as init_mod
    import tgaggerator.repository as repo_mod

    reload(cfg)
    reload(db_mod)
    reload(init_mod)
    reload(repo_mod)

    init_mod.init_db_for_tests()

    with db_mod.SessionLocal() as db:
        channel = repo_mod.upsert_channel(db, tg_id=321, title="Flags", username=None, is_private=True)
        db.commit()

        updated = repo_mod.set_channel_flags(db, channel_id=channel.id, enabled=False, muted=True)
        db.commit()

        assert updated is not None
        assert updated.enabled is False
        assert updated.muted is True


def test_set_channels_flags_batch(tmp_path, monkeypatch):
    db_path = tmp_path / "test_batch_flags.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")

    import tgaggerator.config as cfg
    import tgaggerator.db as db_mod
    import tgaggerator.init_db as init_mod
    import tgaggerator.repository as repo_mod

    reload(cfg)
    reload(db_mod)
    reload(init_mod)
    reload(repo_mod)

    init_mod.init_db_for_tests()

    with db_mod.SessionLocal() as db:
        c1 = repo_mod.upsert_channel(db, tg_id=111, title="A", username="chan_a", is_private=False)
        c2 = repo_mod.upsert_channel(db, tg_id=222, title="B", username=None, is_private=True)
        db.commit()

        updated_ids = repo_mod.set_channels_flags(
            db,
            channel_ids=[c1.id, c2.id],
            enabled=False,
            muted=True,
        )
        db.commit()

    assert len(updated_ids) == 2


def test_message_link_builder():
    from tgaggerator.ingest.dto import MessageDTO

    public_link = MessageDTO._build_link(123456, "mychan", 17)
    private_link = MessageDTO._build_link(-1001234567890, None, 42)

    assert public_link == "https://t.me/mychan/17"
    assert private_link == "https://t.me/c/1234567890/42"


def test_muted_channel_not_ingested(tmp_path, monkeypatch):
    db_path = tmp_path / "test_muted.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")

    import tgaggerator.config as cfg
    import tgaggerator.db as db_mod
    import tgaggerator.init_db as init_mod
    import tgaggerator.repository as repo_mod

    reload(cfg)
    reload(db_mod)
    reload(init_mod)
    reload(repo_mod)

    init_mod.init_db_for_tests()

    with db_mod.SessionLocal() as db:
        c1 = repo_mod.upsert_channel(db, tg_id=100, title="live", username=None, is_private=True)
        c2 = repo_mod.upsert_channel(db, tg_id=200, title="muted", username=None, is_private=True)
        c2.muted = True
        db.commit()

        enabled = repo_mod.get_enabled_channels(db)

    assert [c.id for c in enabled] == [c1.id]
