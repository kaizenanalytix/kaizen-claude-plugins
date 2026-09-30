"""
Env-driven application settings, split by domain.

Copy to app/core/config.py. Values are read from environment variables
(or a local .env file) via pydantic-settings, so nothing environment-
specific is hardcoded in the app.

Config is split into one BaseSettings class per domain (app, database,
CORS, auth) rather than one flat class, so each subsystem's settings are
declared next to the module that owns them and a new domain (email,
storage, ...) is a new nested class, not a growing flat one.

Each domain class carries its own env_file config and reads its own .env
independently — a nested BaseSettings field does NOT automatically inherit
its parent's env-file reading, so this has to be set on every class, not
just Settings. Field(default_factory=...), not a bare `= AppSettings()`
default, defers construction to when Settings() is actually called (inside
get_settings(), below) — a bare instance default would be built once at
import time, before anything has had a chance to read the .env file yet.
Every field still resolves from the same environment/.env file — the split
is organizational, not a change to how values are supplied.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_CONFIG = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class AppSettings(BaseSettings):
    model_config = _ENV_CONFIG

    app_name: str = "backend"
    debug: bool = False


class DatabaseSettings(BaseSettings):
    model_config = _ENV_CONFIG

    database_url: str = "sqlite:///./app.db"


class CORSSettings(BaseSettings):
    model_config = _ENV_CONFIG

    cors_origins: list[str] = ["http://localhost:3000"]


class AuthSettings(BaseSettings):
    model_config = _ENV_CONFIG

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor. Depend on this (via Depends(get_settings) or
    a direct call) rather than instantiating Settings() ad hoc, so the
    whole app shares one parsed configuration. Access a value through its
    domain, e.g. settings.database.database_url, settings.auth.jwt_secret.
    """
    return Settings()
