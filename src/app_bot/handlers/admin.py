from django.conf import settings
from ..loader import bot

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.markdown import hcode, hlink
from aiogram.enums import ParseMode

from asgiref.sync import sync_to_async
from app_bot.keyboards.reply import payed_user_kb
from app_bot.utils.fsm import NewConfig, NewPayment

from app_vpn.models import Purchase, TgUser, Plan
from app_vpn.services.selectors import (
    insert_new_user,
    is_exist_user,
    is_subscription_end,
    get_subscription_end_date
)

router = Router()


@router.callback_query(F.data.startswith("confirm_payment:"))
async def confirm_payment_handler(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMINS:
        await callback.answer("⛔️ У вас нет доступа к этому действию.", show_alert=True)
        return

    purchase_id = int(callback.data.split(":")[1])
    purchase = await sync_to_async(Purchase.objects.select_related("user", "user_plan").get)(id=purchase_id)

    if purchase.successful:
        await callback.answer("❗️ Этот платёж уже был подтверждён.")
        return

    # Отметить как успешный
    purchase.successful = True
    await sync_to_async(purchase.save)()

    # Продлить подписку
    user = purchase.user
    await sync_to_async(user.extend_subscription)(purchase.user_plan.duration_days)

    # Уведомить пользователя
    await bot.send_message(
        user.user_id,
        f"✅ Ваша оплата подтверждена! Подписка продлена до {user.subscription_end_date.strftime('%Y-%m-%d %H:%M')}",
        reply_markup=await payed_user_kb(),
    )

    await callback.message.edit_caption(
        callback.message.caption + "\n\n✅ Оплата подтверждена.",
        reply_markup=None
    )

    await callback.answer("Оплата подтверждена.")