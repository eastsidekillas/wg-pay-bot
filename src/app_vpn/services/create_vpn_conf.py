from .wg_api import create_wg_client, get_client_config
from app_vpn.models import TgUser, VpnClient, Plan
from loguru import logger
from asgiref.sync import sync_to_async


@sync_to_async
def get_active_plan(user: TgUser) -> Plan | None:
    latest_purchase = user.purchases.filter(successful=True).order_by("-created_at").first()
    return latest_purchase.user_plan if latest_purchase else None


@sync_to_async
def get_active_device_count(user: TgUser) -> int:
    return VpnClient.objects.filter(user=user, active=True).count()


async def issue_vpn_config(user: TgUser, device_name: str) -> str | None:
    logger.debug(f"Subscription active: {user.has_active_subscription()}")
    if not user.has_active_subscription():
        return None

    plan = await get_active_plan(user)
    if not plan:
        return None

    current_device_count = await get_active_device_count(user)
    if current_device_count >= plan.max_devices:
        logger.info(f"⚠️ Превышено количество устройств: {current_device_count} / {plan.max_devices}")
        return None

    data = {
        "data": {
            "device": device_name,
            "user_id": user.user_id,
            "username": user.username,
        }
    }

    result = await sync_to_async(create_wg_client)(data)
    if not result:
        return None

    wg_id = result["id"]
    config_name = f"{user.username}_{device_name}"

    # Получаем конфигурационный текст
    config_text = await sync_to_async(get_client_config)(wg_id)
    if not config_text:
        return None

    # Создаём запись в базе
    await create_vpn_client(user, wg_id, config_name)

    return config_text


@sync_to_async
def create_vpn_client(user: TgUser, wg_id: str, config_name: str) -> VpnClient:
    return VpnClient.objects.create(
        user=user,
        wg_id=wg_id,
        config_name=config_name
    )
