"""Environment-backed configuration without embedding deployment secrets."""

from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path


def normalize_database_url(url: str | None) -> str | None:
    """Normalize PostgreSQL connection strings for psycopg v3 and Neon SSL.

    Converts legacy 'postgres://' or standard 'postgresql://' URLs to
    'postgresql+psycopg://' so SQLAlchemy loads the installed psycopg 3 driver.
    Ensures 'sslmode=require' is present for remote hosts such as Neon.
    """
    if not url:
        return None
    url = url.strip()
    if not url:
        return None

    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    if url.startswith("postgresql+psycopg://"):
        try:
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").lower()
            is_local = host in ("localhost", "127.0.0.1", "0.0.0.0", "db", "postgres") or host.endswith(".local")
            if not is_local and host:
                query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
                if "sslmode" not in query_params:
                    query_params["sslmode"] = ["require"]
                    new_query = urllib.parse.urlencode(query_params, doseq=True)
                    url = urllib.parse.urlunparse(parsed._replace(query=new_query))
        except Exception:
            pass

    return url


def _load_dotenv_if_exists() -> None:
    """Load key-value pairs from .env file into os.environ if not already present."""
    candidates = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]
    for p in candidates:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass


_load_dotenv_if_exists()


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str | None
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    llm_provider: str = "gemini"
    llm_api_key: str | None = None
    llm_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = 30.0
    llm_max_tool_calls: int = 5
    llm_max_turns: int = 5
    llm_max_input_length: int = 4000
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


def get_settings() -> Settings:
    raw_env = os.getenv("ENVIRONMENT", "development").strip()
    is_production = raw_env.lower() == "production"

    raw_cors = os.getenv("CORS_ORIGINS", "").strip()
    if raw_cors:
        cors_origins = tuple(origin.strip() for origin in raw_cors.split(",") if origin.strip())
    else:
        cors_origins = ("http://localhost:5173", "http://127.0.0.1:5173")

    if is_production and "*" in cors_origins:
        raise ValueError(
            "Wildcard CORS origin '*' is strictly prohibited in production. "
            "Please configure explicit frontend domain(s) in CORS_ORIGINS."
        )

    database_url = normalize_database_url(os.getenv("DATABASE_URL", "").strip())
    env_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not env_provider:
        if os.getenv("OPENAI_API_KEY") and not (os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")):
            provider = "openai"
        else:
            provider = "gemini"
    else:
        provider = env_provider

    gemini_base_url = (
        os.getenv("GEMINI_BASE_URL", "").strip()
        or "https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    if provider == "gemini":
        api_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
        default_model = "gemini-2.5-flash"
    else:
        api_key = os.getenv("LLM_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        default_model = "gpt-4o-mini"

    model = os.getenv("LLM_MODEL", "").strip() or default_model
    if provider == "gemini" and model in ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"):
        model = "gemini-2.5-flash"

    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
    except ValueError:
        timeout = 30.0
    try:
        max_tool_calls = int(os.getenv("LLM_MAX_TOOL_CALLS", "5"))
    except ValueError:
        max_tool_calls = 5
    try:
        max_turns = int(os.getenv("LLM_MAX_TURNS", "5"))
    except ValueError:
        max_turns = 5
    try:
        max_input_length = int(os.getenv("LLM_MAX_INPUT_LENGTH", "4000"))
    except ValueError:
        max_input_length = 4000

    return Settings(
        environment=raw_env,
        database_url=database_url or None,
        cors_origins=cors_origins,
        llm_provider=provider,
        llm_api_key=api_key or None,
        llm_model=model,
        llm_timeout_seconds=timeout,
        llm_max_tool_calls=max_tool_calls,
        llm_max_turns=max_turns,
        llm_max_input_length=max_input_length,
        gemini_base_url=gemini_base_url,
    )

