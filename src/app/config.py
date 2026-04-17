from dataclasses import dataclass, field

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILES = (".env",)


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    app_env: str = "development"
    api_key: str = "supersecretkey"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES, extra="ignore", env_prefix="POSTGRES_"
    )

    user: str = "payments"
    password: str = "payments"
    db: str = "payments"
    host: str = "localhost"
    port: int = 5432

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES, extra="ignore", env_prefix="RABBITMQ_"
    )

    user: str = "guest"
    password: str = "guest"
    host: str = "localhost"
    port: int = 5672
    payments_queue_name: str = "payments.new"
    dlx_name: str = "dead-letter-exchange"
    payments_dlq_name: str = "payments.new.dlq"
    payments_retry_count: int = 3

    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"


class WebhookSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES, extra="ignore", env_prefix="WEBHOOK_"
    )

    retry_attempts: int = 3


class OutboxSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES, extra="ignore", env_prefix="OUTBOX_"
    )

    poll_interval_seconds: int = 5


@dataclass
class Settings:
    api: APISettings = field(default_factory=APISettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    rabbitmq: RabbitMQSettings = field(default_factory=RabbitMQSettings)
    webhook: WebhookSettings = field(default_factory=WebhookSettings)
    outbox: OutboxSettings = field(default_factory=OutboxSettings)


settings = Settings()
