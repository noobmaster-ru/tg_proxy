# tg_proxy

Telegram-бот для продажи доступа к MTProto-прокси с оплатой в Telegram Stars и ручным подтверждением банковского перевода.

## Структура проекта

- `axiomai_proxy/application` — DTO, исключения, интеракторы (use-cases)
- `axiomai_proxy/infrastructure` — БД, Telegram-представление, DI, логирование
- `axiomai_proxy/tgbot` — Telegram bot entrypoint и handlers
- `axiomai_proxy/observer` — фоновый процесс под периодические задачи
- `axiomai_proxy/infrastructure/database/migrations` — Alembic migrations

## Переменные окружения

- `BOT_TOKEN`
- `ADMIN_IDS`
- `FREE_USER_IDS`
- `POSTGRESQL_HOST`
- `POSTGRESQL_PORT`
- `POSTGRESQL_USER`
- `POSTGRESQL_PASSWORD`
- `POSTGRESQL_DBNAME`
- `SUBSCRIPTION_DAYS`
- `SUBSCRIPTION_PRICE_XTR`
- `SUBSCRIPTION_PRICE_RUB`
- `BANK_CARD_NUMBER`
- `BANK_PHONE_NUMBER`
- `SUPPORT_CONTACT`
- `PROXY_ROTATION_ENABLED`
- `PROXY_SERVER`
- `PROXY_PORT` (для этого проекта держим `9443`)
- `PROXY_CONTAINER_NAME`
- `OBSERVER_POLL_INTERVAL_SECONDS`

## Локальный запуск

```bash
cp .env.example .env
make install
make run-bot
```

Для автосообщений о подписке запусти observer:

```bash
make run-observer
```

## Docker запуск

```bash
docker compose up --build -d
```

В Docker запускаются `bot` и `observer`.

Если используешь `/rotateproxy`, боту нужен доступ к Docker socket хоста
(`/var/run/docker.sock` уже примонтирован в `docker-compose.yaml`).

## Прод-запуск (без контейнера PostgreSQL)

`docker-compose.prod.yaml` — самостоятельный файл для продакшена (только `bot`, `observer`, `migrations`).
Подключение к PostgreSQL берется из `.env` (внешняя БД).

Запуск:

```bash
docker compose -f docker-compose.prod.yaml run --rm migrations
docker compose -f docker-compose.prod.yaml up --build -d bot observer
```

## Миграции

```bash
alembic upgrade head
```

В проде миграции запускаются отдельным сервисом:

```bash
docker compose -f docker-compose.prod.yaml run --rm migrations
```

## Админ-команды

- `/rotateproxy` — создать новый `secret` для контейнера прокси, сохранить новую ссылку в БД и разослать её активным подписчикам.

## Как ограничивается доступ после окончания подписки

Бот проверяет `expires_at` в БД при выдаче ссылки (`Получить прокси`).
Если подписка истекла, ссылка не выдается.

Важно: если у всех пользователей один и тот же MTProto `secret`, ранее сохранённая ссылка может продолжать работать.
Для жесткого отключения нужен отдельный секрет/прокси на сегмент пользователей или ротация секрета.
