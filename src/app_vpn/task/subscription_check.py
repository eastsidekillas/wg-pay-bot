from django.utils import timezone
from app_vpn.models import TgUser, VpnClient
from app_vpn.services.wg_api import disable_wg_client
from app_bot.loader import bot
from loguru import logger
from asgiref.sync import sync_to_async


@sync_to_async
def get_expired_users_with_vpns():
    now = timezone.now()
    # Жадная загрузка связанных VPN-клиентов (через select_related не получится — это ManyToOne)
    expired_users = TgUser.objects.filter(subscription_end_date__lt=now).prefetch_related('vpn_clients')
    return list(expired_users)


@sync_to_async
def get_active_vpns(user):
    return list(user.vpn_clients.filter(active=True))


@sync_to_async
def deactivate_vpn(vpn):
    vpn.active = False
    vpn.save()


async def deactivate_expired_subscriptions():
    expired_users = await get_expired_users_with_vpns()

    for user in expired_users:
        active_vpns = await get_active_vpns(user)

        for vpn in active_vpns:
            success = await disable_wg_client(vpn.wg_id)
            if success:
                await deactivate_vpn(vpn)
                logger.info(f"Отключён WG клиент {vpn.wg_id} пользователя {user.user_id}")
            else:
                logger.warning(f"Не удалось отключить WG клиента {vpn.wg_id}")

        try:
            await bot.send_message(
                user.user_id,
                "❌ Ваша подписка закончилась. Доступ к VPN отключён.\n"
                "Вы можете продлить подписку, чтобы восстановить доступ."
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {user.user_id}: {e}")
