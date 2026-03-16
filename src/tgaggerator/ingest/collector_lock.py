from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path


class CollectorAlreadyRunningError(RuntimeError):
    pass


@contextmanager
def collector_lock(lock_path: str):
    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fh = open(path, "a+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt

            try:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                acquired = True
            except OSError as exc:
                raise CollectorAlreadyRunningError("collector lock is already acquired") from exc
        else:
            import fcntl

            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as exc:
                raise CollectorAlreadyRunningError("collector lock is already acquired") from exc

        fh.seek(0)
        fh.truncate(0)
        fh.write(str(os.getpid()).encode("utf-8"))
        fh.flush()

        yield
    finally:
        try:
            if acquired:
                if os.name == "nt":
                    import msvcrt

                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()
