from asgiref.sync import sync_to_async
from loguru import logger
from django.utils import timezone
from app_vpn.models import TgUser, VpnClient
from app_vpn.services.wg_api import disable_wg_client


@sync_to_async
def insert_new_user(user_id: int, username: str):
    user, created = TgUser.objects.get_or_create(
        user_id=user_id,
        defaults={"username": username},
    )
    return user, created


@sync_to_async
def is_exist_user(user_id: int) -> bool:
    return TgUser.objects.filter(user_id=user_id).exists()


@sync_to_async
def get_user_by_id(user_id: int):
    return TgUser.objects.filter(user_id=user_id).first()


@sync_to_async
def is_user_payed(user_id: int) -> bool:
    user = TgUser.objects.filter(user_id=user_id).first()
    return user.has_active_subscription() if user else False


@sync_to_async
def is_user_have_config(user_id: int) -> bool:
    return VpnClient.objects.filter(user__user_id=user_id, active=True).exists()


@sync_to_async
def all_user_configs(user_id: int) -> list[str] | bool:
    try:
        return list(
            VpnClient.objects.filter(user__user_id=user_id)
            .values_list("config_name", flat=True)
        )
    except Exception as e:
        logger.error(f"[-] {e}")
        return False


async def has_subscription(user_id: int) -> bool:
    return await VpnClient.objects.filter(user__user_id=user_id).aexists()


async def has_active_access(user_id: int) -> bool:
    try:
        user = await TgUser.objects.aget(user_id=user_id)
    except TgUser.DoesNotExist:
        return False
    return user.subscription_end_date and user.subscription_end_date > timezone.now()

@sync_to_async
def is_subscription_end(user_id: int) -> bool:
    try:
        user = TgUser.objects.filter(user_id=user_id).first()
        if not user or not user.subscription_end_date:
            return True  # Нет пользователя или даты — считаем подписку истекшей
        return user.subscription_end_date < timezone.now()
    except Exception as e:
        logger.error(f"[-] {e}")
        return False


@sync_to_async
def get_subscription_end_date(user_id: int) -> str | bool:
    try:
        user = TgUser.objects.filter(user_id=user_id).first()
        if not user or not user.subscription_end_date:
            return False
        return user.subscription_end_date.strftime("%d-%m-%Y")
    except Exception as e:
        logger.error(f"[-] {e}")
        return False



@sync_to_async
def is_subscription_active(user_id: int) -> bool:
    today = timezone.now().date()
    return VpnClient.objects.filter(user__user_id=user_id, active=True, created_at__date=today).exists()


@sync_to_async
def get_subscription_end(user_id: int):
    user = TgUser.objects.filter(user_id=user_id).first()
    return user.subscription_end_date if user else None


@sync_to_async
def get_expired_users_with_clients():
    return TgUser.objects.filter(
        subscription_end_date__lt=timezone.now()
    ).prefetch_related("clients").all()


async def deactivate_expired_vpn_clients():
    expired_users = await get_expired_users_with_clients()

    for user in expired_users:
        logger.info(f"🔒 Отключение конфигов для пользователя {user.username} ({user.user_id})")
        for client in user.clients.all():
            success = await disable_wg_client(client.wg_id)
            if success:
                logger.info(f"🛑 VPN клиент {client.config_name} отключён")
            else:
                logger.warning(f"❌ Не удалось отключить VPN {client.config_name}")