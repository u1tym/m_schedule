from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    db_server: str
    db_port: int
    db_name: str
    db_username: str
    db_password: str

    log_dir: str = "logs"
    log_backup_count: int = 30
    log_level: str = "INFO"

    # 認証 Cookie / JWT（API_LOGIN_SPEC.md）。スケジュール API は検証しないが、受信確認用ログに利用。
    cookie_name: str = "access_token"
    jwt_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    jwt_algorithm: str = "HS256"
    auth_log_jwt_claims: bool = False

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_username}:{self.db_password}"
            f"@{self.db_server}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
