"""Carga variables desde key.env en la raíz del proyecto."""
from pathlib import Path


def load_key_env(base_dir: Path | None = None) -> Path | None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent

    env_path = base_dir / "key.env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
    return env_path if env_path.is_file() else None
