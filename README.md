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

## Локальный запуск

```bash
cp .env.example .env
make install
make run-bot
```

## Docker запуск

```bash
docker compose up --build -d
```

## Миграции

```bash
alembic upgrade head
```

## Как ограничивается доступ после окончания подписки

Бот проверяет `expires_at` в БД при выдаче ссылки (`Получить прокси`).
Если подписка истекла, ссылка не выдается.

Важно: если у всех пользователей один и тот же MTProto `secret`, ранее сохранённая ссылка может продолжать работать.
Для жесткого отключения нужен отдельный секрет/прокси на сегмент пользователей или ротация секрета.
