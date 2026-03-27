from __future__ import annotations

from dataclasses import dataclass

from axiomai_proxy.application.interactors import (
    ApproveBankTransfer,
    ClaimExpiredNotifications,
    ClaimExpiring24hNotifications,
    CreateBankTransferRequest,
    GetPendingBankTransferRequest,
    GetProxyLink,
    GetSubscriptionState,
    GrantSubscription,
    HasProxyAccess,
    ListActiveSubscriptionUserIds,
    ProcessStarsPayment,
    RegisterUser,
    RejectBankTransfer,
    RevokeSubscription,
    SetProxyLink,
)
from axiomai_proxy.config import Config, load_config
from axiomai_proxy.infrastructure.database.gateways import PostgresSubscriptionGateway
from axiomai_proxy.infrastructure.database.postgres import PostgresDatabase
from axiomai_proxy.infrastructure.proxy import ProxySecretRotator


@dataclass(frozen=True)
class Interactors:
    register_user: RegisterUser
    get_subscription_state: GetSubscriptionState
    has_proxy_access: HasProxyAccess
    get_proxy_link: GetProxyLink
    set_proxy_link: SetProxyLink
    process_stars_payment: ProcessStarsPayment
    create_bank_transfer_request: CreateBankTransferRequest
    get_pending_bank_transfer_request: GetPendingBankTransferRequest
    approve_bank_transfer: ApproveBankTransfer
    reject_bank_transfer: RejectBankTransfer
    grant_subscription: GrantSubscription
    revoke_subscription: RevokeSubscription
    list_active_subscription_user_ids: ListActiveSubscriptionUserIds
    claim_expiring_24h_notifications: ClaimExpiring24hNotifications
    claim_expired_notifications: ClaimExpiredNotifications


@dataclass(frozen=True)
class AppContainer:
    config: Config
    database: PostgresDatabase
    gateway: PostgresSubscriptionGateway
    interactors: Interactors
    proxy_secret_rotator: ProxySecretRotator | None


async def build_container() -> AppContainer:
    config = load_config()
    database = PostgresDatabase(config.postgres_dsn)
    await database.connect()

    gateway = PostgresSubscriptionGateway(database.engine)

    get_subscription_state = GetSubscriptionState(gateway=gateway, free_user_ids=config.free_user_ids)

    interactors = Interactors(
        register_user=RegisterUser(gateway=gateway),
        get_subscription_state=get_subscription_state,
        has_proxy_access=HasProxyAccess(get_subscription_state=get_subscription_state),
        get_proxy_link=GetProxyLink(gateway=gateway),
        set_proxy_link=SetProxyLink(gateway=gateway),
        process_stars_payment=ProcessStarsPayment(gateway=gateway, subscription_days=config.subscription_days),
        create_bank_transfer_request=CreateBankTransferRequest(gateway=gateway),
        get_pending_bank_transfer_request=GetPendingBankTransferRequest(gateway=gateway),
        approve_bank_transfer=ApproveBankTransfer(gateway=gateway, subscription_days=config.subscription_days),
        reject_bank_transfer=RejectBankTransfer(gateway=gateway),
        grant_subscription=GrantSubscription(gateway=gateway),
        revoke_subscription=RevokeSubscription(gateway=gateway),
        list_active_subscription_user_ids=ListActiveSubscriptionUserIds(gateway=gateway),
        claim_expiring_24h_notifications=ClaimExpiring24hNotifications(gateway=gateway),
        claim_expired_notifications=ClaimExpiredNotifications(gateway=gateway),
    )

    proxy_secret_rotator: ProxySecretRotator | None = None
    if config.proxy_rotation_enabled:
        proxy_secret_rotator = ProxySecretRotator(
            server=config.proxy_server,
            port=config.proxy_port,
            container_name=config.proxy_container_name,
        )

    return AppContainer(
        config=config,
        database=database,
        gateway=gateway,
        interactors=interactors,
        proxy_secret_rotator=proxy_secret_rotator,
    )


async def close_container(container: AppContainer) -> None:
    await container.database.close()
