from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app_vpn.models import Plan, VpnClient
from asgiref.sync import sync_to_async


@sync_to_async
def get_user_configs_kb(user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    configs = VpnClient.objects.filter(user__user_id=user_id, active=True)

    for config in configs:
        buttons.append([
            InlineKeyboardButton(
                text=config.config_name,
                callback_data=f"get_config:{config.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="➕ Создать конфиг",
            callback_data="create_config"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@sync_to_async
def get_plan_buttons():
    keyboard = []
    for plan in Plan.objects.all():
        keyboard.append([
            InlineKeyboardButton(
                text=f"{plan.name} — {plan.price}₽",
                callback_data=f"choose_plan:{plan.id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirm_payment_kb(purchase_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Подтвердить оплату",
            callback_data=f"confirm_payment:{purchase_id}"
        )]
    ])


async def cancel_payment_kb():
    keyboard = [
        [InlineKeyboardButton(text="❌Отмена❌", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
