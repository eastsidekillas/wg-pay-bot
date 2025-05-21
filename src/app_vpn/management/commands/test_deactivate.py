from django.core.management.base import BaseCommand
import asyncio
from app_vpn.task.subscription_check import deactivate_expired_subscriptions


class Command(BaseCommand):
    help = 'Тестовая деактивация пользователей с истекшей подпиской'

    def handle(self, *args, **options):
        asyncio.run(deactivate_expired_subscriptions())
