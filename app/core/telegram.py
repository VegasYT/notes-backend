import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def notify_error(path: str, method: str, error: str, tb: str = "") -> None:
    """Отправляет уведомление о 500-й ошибке в Telegram.

    Если токен или chat_id не заданы - молча пропускает.
    Traceback обрезается до 3500 символов из-за лимита Telegram (4096)
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id_list:
        return

    tb_truncated = tb[-3500:] if len(tb) > 3500 else tb

    text = (
        "🚨 *Internal Server Error*\n"
        f"*Path:* `{method} {path}`\n"
        f"*Error:* `{error}`\n\n"
        f"```\n{tb_truncated}\n```"
    )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            for chat_id in settings.telegram_chat_id_list:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                })
    except Exception:
        logger.warning("Не удалось отправить уведомление в Telegram")
