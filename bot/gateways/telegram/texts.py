from __future__ import annotations

from datetime import UTC, datetime

from bot.domain.models import SubscriptionState


BUTTON_GET_PROXY = "Получить прокси"
BUTTON_SUB_STATUS = "Статус подписки"
BUTTON_BUY_SUB = "Купить gподписку"
BUTTON_BANK_TRANSFER = "Оплата переводом"
BUTTON_HELP = "Помощь"
BUTTON_I_PAID = "Я оплатил"

ADMIN_ACTION_CONFIRM = "Подтвердить"
ADMIN_ACTION_REJECT = "Отклонить"


def format_subscription_state(state: SubscriptionState) -> str:
    if state.is_free:
        return "активна (бесплатный доступ для вашего аккаунта)"

    expiry = state.expires_at
    if expiry is None:
        return "не активна"

    now = datetime.now(UTC)
    if expiry <= now:
        return f"истекла {expiry.strftime('%Y-%m-%d %H:%M UTC')}"

    remaining = expiry - now
    days_left = remaining.days
    hours_left = remaining.seconds // 3600
    return f"активна до {expiry.strftime('%Y-%m-%d %H:%M UTC')} (осталось {days_left}д {hours_left}ч)"


def start_message() -> str:
    return (
        "Этот бот выдает доступ к вашему приватному Telegram-прокси по подписке.\n\n"
        "Используйте кнопки ниже: купить подписку, оплатить переводом и получить ссылку на прокси."
    )


def help_message() -> str:
    return (
        "Команды пользователя:\n"
        "/start — открыть меню\n"
        "/help — справка\n"
        "/support — поддержка\n"
        "/paysupport — поддержка по оплате\n\n"
        "Кнопки:\n"
        "Купить подписку — оплата Telegram Stars\n"
        "Оплата переводом — перевод на карту/СБП и подтверждение админом\n\n"
        "Команды админа:\n"
        "/setproxy <t.me или tg:// ссылка>\n"
        "/grant <user_id> <days>\n"
        "/revoke <user_id>\n"
        "/check <user_id>"
    )


def support_message(contact: str) -> str:
    return f"Поддержка: {contact}"


def payment_support_message(contact: str) -> str:
    return f"Поддержка по оплате: {contact}"


def no_subscription_message() -> str:
    return "У вас нет активной подписки. Сначала оформите подписку."


def proxy_not_configured_message() -> str:
    return "Ссылка на прокси пока не настроена. Обратитесь в поддержку."


def proxy_link_message(proxy_link: str) -> str:
    return (
        "Ваша ссылка на прокси:\n"
        f"{proxy_link}\n\n"
        "Нажмите на ссылку и подтвердите подключение в Telegram."
    )


def free_access_message() -> str:
    return "Для вашего аккаунта доступ включен без оплаты."


def bank_transfer_instructions(card: str, phone: str, amount_rub: int, days: int) -> str:
    return (
        "Оплата переводом:\n"
        f"Сумма: {amount_rub} ₽\n"
        f"Карта: {card}\n"
        f"Телефон (СБП): {phone}\n\n"
        f"После оплаты нажмите «{BUTTON_I_PAID}». Срок подписки: {days} дней."
    )


def bank_transfer_pending_exists_message() -> str:
    return "У вас уже есть заявка в обработке. Дождитесь решения админа или напишите в поддержку."


def bank_transfer_request_sent_message() -> str:
    return "Заявка отправлена админу. Ожидайте подтверждения оплаты."


def bank_transfer_admin_notification(request_id: int, user_id: int, username: str, amount_rub: int, days: int) -> str:
    return (
        "Новая заявка на оплату переводом\n"
        f"request_id={request_id}\n"
        f"user_id={user_id}\n"
        f"username={username}\n"
        f"сумма={amount_rub} ₽\n"
        f"тариф={days} дней\n\n"
        "Подтверждайте только после поступления денег."
    )


def bank_transfer_confirmed_user(expiry: datetime) -> str:
    return (
        "Оплата переводом подтверждена. Подписка активирована.\n"
        f"Доступ активен до {expiry.strftime('%Y-%m-%d %H:%M UTC')}."
    )


def bank_transfer_rejected_user() -> str:
    return "Заявка отклонена. Если вы уже оплатили, обратитесь в поддержку."


def stars_payment_success_message(expiry: datetime) -> str:
    return (
        "Оплата получена. Подписка активирована.\n"
        f"Доступ активен до {expiry.strftime('%Y-%m-%d %H:%M UTC')}."
    )


def stars_payment_admin_notification(user_id: int, amount: int, currency: str, expiry: datetime) -> str:
    return (
        "Новая оплата Stars:\n"
        f"user_id={user_id}\n"
        f"amount={amount} {currency}\n"
        f"expires={expiry.strftime('%Y-%m-%d %H:%M UTC')}"
    )


def admin_proxy_updated_message() -> str:
    return "Ссылка прокси обновлена."


def admin_usage_setproxy() -> str:
    return "Использование: /setproxy <https://t.me/proxy?...>"


def admin_invalid_proxy_message() -> str:
    return "Ссылка должна начинаться с https://t.me/proxy? или tg://proxy?"


def admin_usage_grant() -> str:
    return "Использование: /grant <user_id> <days>"


def admin_usage_revoke() -> str:
    return "Использование: /revoke <user_id>"


def admin_usage_check() -> str:
    return "Использование: /check <user_id>"


def admin_numbers_required_message() -> str:
    return "user_id и days должны быть числами"


def admin_user_id_number_required_message() -> str:
    return "user_id должен быть числом"


def admin_days_positive_message() -> str:
    return "days должен быть положительным"


def admin_grant_done_message(user_id: int, expiry: datetime) -> str:
    return f"Подписка обновлена: {user_id} -> {expiry.strftime('%Y-%m-%d %H:%M UTC')}"


def admin_revoke_done_message(user_id: int) -> str:
    return f"Подписка отключена для user_id={user_id}"


def admin_check_message(user_id: int, state: SubscriptionState) -> str:
    return f"Пользователь {user_id}: {format_subscription_state(state)}"


def fallback_message() -> str:
    return "Используйте кнопки меню или /help"
