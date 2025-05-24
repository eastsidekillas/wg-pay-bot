from django.db import models
from django.utils import timezone
from datetime import timedelta


class TgUser(models.Model):
    user_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    is_trial_used = models.BooleanField(default=False)

    def has_active_subscription(self) -> bool:
        return self.subscription_end_date and self.subscription_end_date > timezone.now()

    def extend_subscription(self, days: int):
        now = timezone.now()
        if self.subscription_end_date and self.subscription_end_date > now:
            # Подписка активна — продлеваем от текущей даты окончания
            self.subscription_end_date += timedelta(days=days)
        else:
            # Подписка неактивна или отсутствует — начинаем с текущего момента
            self.subscription_end_date = now + timedelta(days=days)
        self.save()


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)  # например: 299.00
    duration_days = models.PositiveIntegerField()  # срок действия в днях
    description = models.TextField(blank=True)
    max_devices = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.duration_days} дней за {self.price}₽"


class Purchase(models.Model):
    user = models.ForeignKey(TgUser, on_delete=models.CASCADE, related_name="purchases")
    is_trial = models.BooleanField(default=False)
    user_plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} → {self.user_plan.name} ({'успешно' if self.successful else 'неудачно'})"


class VpnClient(models.Model):
    user = models.ForeignKey(TgUser, related_name="vpn_clients", on_delete=models.CASCADE)
    wg_id = models.IntegerField(unique=True)
    config_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.config_name} (WG ID: {self.wg_id})"
