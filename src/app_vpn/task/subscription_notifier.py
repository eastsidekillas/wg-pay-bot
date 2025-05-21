from django.utils import timezone
from app_vpn.models import TgUser
from app_bot.loader import bot
from app_bot.keyboards.reply import free_user_kb
from loguru import logger
from datetime import timedelta
from asgiref.sync import sync_to_async


@sync_to_async
def get_users_with_expiring_subscriptions():
    warn_date = timezone.now() + timedelta(days=3)
    return list(TgUser.objects.filter(subscription_end_date__date=warn_date.date()))


async def notify_users_about_expiring_subscriptions():
    users = await get_users_with_expiring_subscriptions()

    for user in users:
        try:
            await bot.send_message(
                user.user_id,
                "⚠️ Через 3 дня истекает срок действия вашей подписки.\n"
                "Пожалуйста, продлите её, чтобы избежать отключения VPN.",
                reply_markup=await free_user_kb(user.user_id),
            )
            logger.info(f"Уведомление отправлено пользователю {user.user_id}")
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
