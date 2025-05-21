from django.core.management.base import BaseCommand
import asyncio
from app_vpn.task.subscription_notifier import notify_users_about_expiring_subscriptions


class Command(BaseCommand):
    help = 'Тестовая отправка уведомлений за 3 дня до окончания подписки'

    def handle(self, *args, **options):
        asyncio.run(notify_users_about_expiring_subscriptions())
