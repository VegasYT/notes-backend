from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Центральная конфигурация, загружаемая из .env файла"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_user: str = "notes_user"
    postgres_password: str = "notes_password"
    postgres_db: str = "notes_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_session_ttl: int = 86400  # время жизни сессии в секундах

    # MongoDB
    mongo_host: str = "mongodb"
    mongo_port: int = 27017
    mongo_db: str = "notes_logs"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "app_events"

    # Приложение
    secret_key: str = "ultra_mega_secret_:)"
    debug: bool = False

    # Telegram (опционально - уведомления о 500-х ошибках)
    # Несколько chat_id указываются через запятую: "123,456,789"
    telegram_bot_token: str | None = None
    telegram_chat_ids: str = ""

    @property
    def telegram_chat_id_list(self) -> list[str]:
        """Возвращает список chat_id из строки с разделителем-запятой"""
        if not self.telegram_chat_ids:
            return []
        return [cid.strip() for cid in self.telegram_chat_ids.split(",") if cid.strip()]

    @property
    def postgres_dsn(self) -> str:
        """Асинхронный dsn для SQLAlchemy + asyncpg"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def mongo_url(self) -> str:
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"


settings = Settings()
