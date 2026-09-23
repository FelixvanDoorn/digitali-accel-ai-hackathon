from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENGINE_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ENGINE_DIR.parent


def _shared_dir(name: str) -> Path:
    """templates/ and prompts/ live at the repo root; deploys that only upload engine/ (Vercel) copy them
    into engine/ first (scripts/deploy_vercel.sh)."""
    bundled = ENGINE_DIR / name
    return bundled if bundled.is_dir() else REPO_DIR / name


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENGINE_DIR / ".env", extra="ignore", env_ignore_empty=True)

    # The key comes from NEBIUS_API_KEY if set, otherwise from the key file.
    nebius_api_key: str = ""
    nebius_key_file: Path = REPO_DIR / "nebius_token.env"
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    vision_model: str = ""
    text_model: str = ""

    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    # Also allow origins matching this regex, e.g. every Vercel preview URL of the frontend project.
    allowed_origin_regex: str | None = None
    # If set, /extract requires this value in the X-API-Key header (e.g. from the website's server).
    engine_api_key: str = ""
    templates_dir: Path = _shared_dir("templates")
    prompts_dir: Path = _shared_dir("prompts")
    # Empty means photos are never stored. Set a folder to keep uploads (e.g. for building the eval set).
    save_uploads_dir: Path | None = None

    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_edge: int = 2000


settings = Settings()


class ConfigError(RuntimeError):
    """Setup problem the person running the engine can fix; the message says how."""


def _read_key_file(path: Path) -> str:
    """Accepts either a bare token or a NEBIUS_API_KEY=... line."""
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line and line.split("=", 1)[0].strip().isidentifier():
            name, value = line.split("=", 1)
            if name.strip() != "NEBIUS_API_KEY":
                continue
            line = value
        return line.strip().strip("'\"")
    return ""


def nebius_api_key() -> str:
    if settings.nebius_api_key:
        return settings.nebius_api_key

    path = settings.nebius_key_file
    if not path.is_file():
        raise ConfigError(
            f"No Nebius API key found. Expected a key file at {path}.\n"
            "To fix, either:\n"
            "  1. Create an API key at https://tokenfactory.nebius.com (API keys page) and save it,\n"
            f"     on its own, in {path}\n"
            "  2. Or set NEBIUS_API_KEY in engine/.env or your shell.\n"
            "Then restart the engine."
        )
    key = _read_key_file(path)
    if not key:
        raise ConfigError(
            f"The key file {path} is empty.\n"
            "To fix: paste your Token Factory API key into it (the bare key, or NEBIUS_API_KEY=<key>), "
            "then restart the engine."
        )
    return key


def check_model_config() -> None:
    """Raises ConfigError with fix steps if the engine cannot call Token Factory."""
    nebius_api_key()
    if not settings.vision_model:
        raise ConfigError(
            "VISION_MODEL is not set.\n"
            "To fix: add VISION_MODEL=<model id> to engine/.env. List the available models with:\n"
            f'  curl -H "Authorization: Bearer $(cat {settings.nebius_key_file})" {settings.nebius_base_url}models\n'
            "Then restart the engine."
        )
