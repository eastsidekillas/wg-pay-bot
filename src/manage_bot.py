import asyncio
import os
import django
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chill_vpn.settings')
django.setup()


async def main():
    try:
        from app_bot.loader import bot, dp
        from app_bot.handlers import user, admin
        from app_vpn.task.subscription_notifier import notify_users_about_expiring_subscriptions
        from app_vpn.task.subscription_check import deactivate_expired_subscriptions

        dp.include_router(user.router)
        dp.include_router(admin.router)

        # Планировщик
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            notify_users_about_expiring_subscriptions,
            CronTrigger(hour=9, minute=0),  # Каждый день в 9:00 утра
            id="notify_expiring_users",
            replace_existing=True,
        )
        # Запускаем каждый день в полночь
        scheduler.add_job(
            deactivate_expired_subscriptions,
            CronTrigger(hour=0, minute=0),
            name="Отключение VPN при истечении подписки",
        )
        scheduler.start()

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception("Bot crashed with error:")


if __name__ == "__main__":
    asyncio.run(main())
