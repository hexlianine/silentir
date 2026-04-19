"""Load `.env` / `.env.local` for example scripts when `python-dotenv` is installed."""

from __future__ import annotations

from pathlib import Path


def load_dotenv_in_directories(*directories: Path) -> None:
    """Merge env files into ``os.environ`` for each directory, in order.

    For each directory: loads ``.env`` without overriding existing keys, then
    ``.env.local`` with override so local values win. No-op if ``python-dotenv``
    is not installed.
    """
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return

    for directory in directories:
        env_path = directory / ".env"
        local_path = directory / ".env.local"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
        if local_path.is_file():
            load_dotenv(local_path, override=True)
