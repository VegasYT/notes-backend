import asyncio
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.kafka.events import AppEvent

logger = logging.getLogger(__name__)

# Глобальный producer - инициализируется в lifespan приложения
_producer: AIOKafkaProducer | None = None


async def init_producer(retries: int = 10, delay: float = 3.0) -> None:
    """Запускает Kafka producer с повторными попытками при недоступности брокера """
    global _producer
    for attempt in range(1, retries + 1):
        try:
            _producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
            await _producer.start()
            logger.info("Kafka producer запущен")
            return
        except Exception:
            logger.warning("Kafka недоступна, попытка %d/%d...", attempt, retries)
            _producer = None
            if attempt < retries:
                await asyncio.sleep(delay)
    logger.error("Не удалось подключиться к Kafka после %d попыток - продолжаем без неё", retries)


async def stop_producer() -> None:
    """Останавливает Kafka producer. Вызывается при завершении приложения"""
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
        logger.info("Kafka producer остановлен")


async def send_event(event: AppEvent) -> None:
    """Сериализует событие в JSON и отправляет в топик Kafka"""
    if _producer is None:
        logger.warning("Kafka producer не инициализирован, событие пропущено: %s", event.event_type)
        return

    try:
        data = event.model_dump_json().encode("utf-8")
        await _producer.send_and_wait(settings.kafka_topic, data)
    except Exception:
        logger.exception("Ошибка отправки события в Kafka: %s", event.event_type)
