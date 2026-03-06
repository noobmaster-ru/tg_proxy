# tg_proxy

MVP stack for private Telegram proxy distribution by subscription:

- your own MTProto proxy (Docker)
- Telegram bot for issuing proxy link only to active subscribers
- automatic subscription activation after Telegram Stars payment
- admin commands for manual access control

## Important security note

A public third-party MTProto proxy can see metadata (your IP, connection time, traffic volume),
but cannot decrypt Telegram message content.

If you run your own proxy, you reduce trust in unknown third parties.

## 1. Deploy your own proxy

Use files in [`mtproxy/`](./mtproxy). Quick run:

```bash
cd mtproxy
docker compose up -d
docker logs mtproto-proxy
```

Take the generated `https://t.me/proxy?...` link from logs.

## 2. Configure bot

```bash
cp .env.example .env
```

Set values in `.env`:

- `BOT_TOKEN` from `@BotFather`
- `ADMIN_IDS` with your Telegram user ID
- `SUBSCRIPTION_DAYS`
- `SUBSCRIPTION_PRICE_XTR` (price in Telegram Stars)
- `SUPPORT_CONTACT` and `TERMS_URL` (required by Telegram payments rules)

## 3. Run bot locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

Or with Docker:

```bash
docker compose up --build -d
```

## 4. Set proxy link in bot

In Telegram (as admin):

```text
/setproxy https://t.me/proxy?server=...&port=...&secret=...
```

Now users with active subscription can tap `Get proxy` and receive this link.

## User flow

1. User presses `Buy subscription`
2. Bot sends Telegram Stars invoice (`XTR`)
3. After successful payment, bot extends subscription automatically
4. User presses `Get proxy` and receives MTProto link

## Admin commands

- `/setproxy <link>`: set/update proxy link
- `/grant <user_id> <days>`: grant or extend access manually
- `/revoke <user_id>`: remove access
- `/check <user_id>`: check user subscription state
- `/support`, `/terms`, `/paysupport`: payment compliance/support endpoints

## Telegram payments policy

For digital goods/services in bots (like proxy access), Telegram requires payments in Stars (`XTR`).
This project uses Stars invoices by default.
# tg_proxy
