import asyncio
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.db.mongo_client import get_mongo_db
from app.kafka.events import AppEvent

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None


async def _consume_loop() -> None:
    """Основной цикл чтения событий из Kafka и записи в MongoDB

    Запускается как фоновый asyncio.Task в lifespan приложения.
    При недоступности брокера повторяет попытки подключения
    """
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="notes-logger",
        auto_offset_reset="earliest",
        # aiokafka сам переподключается, но даём запас на старт
        retry_backoff_ms=2000,
    )

    # Ждём доступности Kafka перед стартом
    for attempt in range(1, 11):
        try:
            await consumer.start()
            break
        except Exception:
            logger.warning("Consumer: Kafka недоступна, попытка %d/10...", attempt)
            if attempt == 10:
                logger.error("Consumer: не удалось подключиться к Kafka, worker остановлен")
                return
            await asyncio.sleep(3)

    logger.info("Kafka consumer запущен, топик: %s", settings.kafka_topic)

    try:
        async for message in consumer:
            try:
                event = AppEvent.model_validate_json(message.value)
                db = get_mongo_db()
                # Сохраняем документ в коллекцию events
                await db["events"].insert_one(event.model_dump())
            except Exception:
                logger.exception("Ошибка обработки сообщения из Kafka")
    finally:
        await consumer.stop()
        logger.info("Kafka consumer остановлен")


async def start_consumer() -> None:
    """Запускает consumer как фоновый asyncio.Task"""
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())


async def stop_consumer() -> None:
    """Отменяет фоновый consumer task"""
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
