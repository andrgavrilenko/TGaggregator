from importlib import reload

import pytest


def test_collector_lock_single_writer(tmp_path, monkeypatch):
    lock_path = tmp_path / "collector.lock"
    monkeypatch.setenv("COLLECTOR_LOCK_PATH", str(lock_path))

    import tgaggerator.config as cfg
    import tgaggerator.ingest.collector_lock as lock_mod

    reload(cfg)
    reload(lock_mod)

    with lock_mod.collector_lock(str(lock_path)):
        with pytest.raises(lock_mod.CollectorAlreadyRunningError):
            with lock_mod.collector_lock(str(lock_path)):
                pass
