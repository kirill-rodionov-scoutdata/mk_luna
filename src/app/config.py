import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict

# Build the list of env files: base .env always loaded first;
# .env.test (if present) is loaded second so its values win — this lets
# local test runs override POSTGRES_HOST without touching .env or Docker configs.
_ENV_FILES: tuple[str, ...] = (".env",)
if pathlib.Path(".env.test").exists():
    _ENV_FILES = (".env", ".env.test")


class Settings(BaseSettings):
    """
    Central configuration loaded from environment variables / .env file.
    All infra components read from this single source of truth.
    """

    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    # Application
    app_env: str = "development"
    api_key: str = "supersecretkey"

    # Database
    postgres_user: str = "payments"
    postgres_password: str = "payments"
    postgres_db: str = "payments"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # RabbitMQ
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672

    # Outbox relay
    outbox_poll_interval_seconds: int = 5
    webhook_retry_attempts: int = 3

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )


settings = Settings()
