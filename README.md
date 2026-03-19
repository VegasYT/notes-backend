# Notes Backend

Backend для системы управления заметками с изоляцией данных между пользователями.

## Стек
| | |
|---|---|
| **FastAPI** | веб-фреймворк |
| **PostgreSQL + SQLAlchemy** | основная БД (пользователи, дашборды, заметки) |
| **Alembic** | миграции БД |
| **Redis** | хранение сессий (session:{uuid} → user_id, TTL 24ч) |
| **MongoDB** | аудит-лог событий |
| **Kafka (KRaft)** | брокер событий |
| **Nginx** | reverse proxy + auth_request |
| **Docker Compose** | оркестрация |

## Быстрый старт

```bash
cp .env.example .env        # заполнить переменные
docker compose up -d --build
```

- **Swagger UI:** `http://localhost/joqendo32jr923JIDWd2wkdw4`
- **Админ-панель:** `http://localhost/admin` (требует `is_admin=true` в БД)

## Архитектура

```
Роутер → Сервис → Репозиторий
```

Сервисы бросают доменные исключения (`NotFoundError`, `ForbiddenError` и т.д.) - не знают про HTTP.
Middleware в `main.py` конвертирует их в JSON-ответы централизованно.

```
app/
├── api/v1/          # HTTP-слой: роутеры, валидация входных данных
├── services/        # Бизнес-логика, проверка прав
├── db/
│   ├── postgres/    # ORM-модели + репозитории (DAL)
│   ├── redis_client.py
│   └── mongo_client.py
├── kafka/           # Producer + Consumer (фоновый asyncio Task)
├── schemas/         # Pydantic-схемы запросов/ответов
└── core/            # Config, exceptions, security, dependencies
```

## Аутентификация

- Сессии хранятся в Redis: `session:{uuid4} → user_id`
- Cookie `session_id` (httponly, samesite=lax) передаётся с каждым запросом
- Nginx проверяет сессию через `auth_request /api/auth/verify` перед проксированием
- Публичные эндпоинты (без проверки): `/api/v1/auth/register`, `/api/v1/auth/login`

## Изоляция данных

- Каждый пользователь видит только свои дашборды и заметки
- Владелец может расшарить дашборд с уровнем `read` или `write`
- `write` - чтение + редактирование, `read` - только чтение, удалять может только владелец

## События (Kafka -> MongoDB)

После ключевых действий producer отправляет событие в топик `app_events`.
Consumer (фоновый asyncio Task) читает топик и сохраняет документы в MongoDB.

Типы событий: `user.registered`, `user.logged_in`, `user.logged_out`,
`dashboard.created/updated/deleted/shared`, `note.created/updated/deleted`, `error.occurred`.

При 500-ошибках: traceback логируется в MongoDB и отправляется в Telegram (если настроен).

## Админ-панель

`http://localhost/admin` - sqladmin UI: просмотр пользователей, дашбордов, заметок, доступов и лога событий из MongoDB с фильтрацией.

**REST API** (требует `is_admin=true`):
- `GET /api/v1/admin/events` - события из MongoDB
- `GET /api/v1/admin/users` - список пользователей
- `DELETE /api/v1/admin/users/{id}` - удалить пользователя

## Миграции

```bash
# Генерация (локально, нужен POSTGRES_HOST=localhost в .env)
alembic revision --autogenerate -m "описание"
```

## Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `POSTGRES_USER/PASSWORD/DB/HOST` | Подключение к PostgreSQL |
| `REDIS_HOST` | Хост Redis |
| `MONGO_HOST` | Хост MongoDB |
| `KAFKA_BOOTSTRAP_SERVERS` | Адрес Kafka брокера |
| `SECRET_KEY` | Секретный ключ (сессии) |
| `TELEGRAM_BOT_TOKEN` | Токен бота (опционально) |
| `TELEGRAM_CHAT_IDS` | ID чатов через запятую (опционально) |

## Тесты

```bash
pytest tests/
```

- `tests/unit/` - unit-тесты сервисов (без внешних зависимостей)
- `tests/integration/` - e2e тесты API (SQLite in-memory + мок Redis/Kafka)


## Выдача админки через докер
```bash
docker exec notes_postgres psql -U postgres -d notes_db -c "update users set is_admin = true where id = <id созданного пользователя>;"
```

### 🗄️ Архитектура БД
![DB](https://i.imgur.com/T3NFqaN.png)
