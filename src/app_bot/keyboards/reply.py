from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app_vpn.services.selectors import is_user_have_config


async def payed_user_kb():
    keyboard = [
        [KeyboardButton(text="📁 Мои конфиги"), KeyboardButton(text="💳 Тарифы")],
        [KeyboardButton(text="🕑 Моя подписка"), KeyboardButton(text="📝 Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def free_user_kb(user_id: int):
    row = [KeyboardButton(text="💵 Оплатить")]
    if await is_user_have_config(user_id=user_id):
        row.append(KeyboardButton(text="📁 Мои конфиги"))
    keyboard = [row]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def back_to_main_menu_kb():
    keyboard = [
        [KeyboardButton(text="🔙 Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

