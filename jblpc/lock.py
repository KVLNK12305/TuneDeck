"""
Single instance lock implementation for TuneDeck.

Prevents concurrent second instance from corrupting device state or locking RFCOMM sockets.
"""

import os
import fcntl
from pathlib import Path
from typing import Optional
from .exceptions import InstanceLockError


class SingleInstanceLock:
    """Acquires an exclusive flock on an instance lockfile."""

    def __init__(self, lock_dir: Optional[Path] = None, name: str = "jblpc.lock", lock_name: Optional[str] = None):
        if lock_name:
            name = lock_name
        if lock_dir is None:
            xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
            if xdg_runtime:
                base = Path(xdg_runtime)
            else:
                xdg_config = os.environ.get("XDG_CONFIG_HOME")
                base = Path(xdg_config) if xdg_config else Path.home() / ".config"
            lock_dir = base / "jblpc"
        self.lock_path = lock_dir / name
        self._file = None
        self._cleanup_error: Optional[str] = None

    def acquire(self):
        """Acquire lock or raise InstanceLockError if another instance holds it."""
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.lock_path, "w")
            fcntl.flock(self._file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._file.write(f"{os.getpid()}\n")
            self._file.flush()
        except (IOError, OSError) as e:
            if self._file:
                try:
                    self._file.close()
                except OSError as err:
                    self._cleanup_error = str(err)
                self._file = None
            raise InstanceLockError(f"Another instance of JBLPc is already running (locked by {self.lock_path}).") from e

    def release(self):
        """Release the instance lock and remove the lockfile."""
        if self._file:
            try:
                fcntl.flock(self._file, fcntl.LOCK_UN)
                self._file.close()
            except OSError as err:
                self._cleanup_error = str(err)
            self._file = None
            try:
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except OSError as err:
                self._cleanup_error = str(err)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
