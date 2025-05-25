from django.conf import settings
from django.utils import timezone
from ..loader import bot
from asgiref.sync import sync_to_async

from io import BytesIO
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.markdown import hcode, hlink
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile

from app_bot.keyboards.reply import free_user_kb, payed_user_kb, back_to_main_menu_kb
from app_bot.keyboards.inline import cancel_payment_kb, confirm_payment_kb, get_plan_buttons, get_user_configs_kb
from app_bot.utils.fsm import NewConfig, NewPayment

from app_vpn.models import Purchase, TgUser, Plan, VpnClient
from app_vpn.services.selectors import insert_new_user, is_exist_user, is_subscription_end, get_subscription_end_date, \
    get_user_by_id, has_subscription, has_active_access, is_user_payed
from app_vpn.services.wg_api import download_config_file, get_qr_code
from app_vpn.services.create_vpn_conf import issue_vpn_config

from app_vpn.task.subscription_notifier import notify_users_about_expiring_subscriptions

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if not message.from_user.username:
        await message.answer(
            f"Привет, {message.from_user.full_name}!\nУ тебя не установлен username, установи его в"
            " настройках телеграма и напиши /start\nЕсли не знаешь как это сделать — посмотри"
            f" {hlink('справку', 'https://silverweb.by/kak-sozdat-nik-v-telegramm/')}",
            parse_mode=ParseMode.HTML,
        )
        return

    # Проверка существующего пользователя
    if await is_exist_user(message.from_user.id):
        if not await has_active_access(message.from_user.id):
            await message.answer(
                f"Привет, {message.from_user.full_name or message.from_user.username}, у тебя нет активной подписки.\n"
                "Оплати её, чтобы начать пользоваться VPN.",
                reply_markup=await free_user_kb(message.from_user.id),
            )
        else:
            end_date = await get_subscription_end_date(message.from_user.id)
            await message.answer(
                f"Привет, {message.from_user.full_name or message.from_user.username}, твоя"
                f" подписка действительна до {end_date}",
                reply_markup=await payed_user_kb(),
            )
        return

    # Новый пользователь
    user, created = await insert_new_user(message.from_user.id, message.from_user.username)

    # Если пользователь не использовал пробный период
    if not user.is_trial_used:
        user.subscription_end_date = timezone.now() + timezone.timedelta(days=7)
        user.is_trial_used = True
        await sync_to_async(user.save)()

        await message.answer(
            f"🎉 Вам предоставлен бесплатный пробный доступ на 7 дней!\n"
            f"📆 Подписка активна до {user.subscription_end_date.strftime('%d.%m.%Y')}",
            reply_markup=await payed_user_kb()
        )
    else:
        await message.answer(
            f"Привет, {message.from_user.full_name or message.from_user.username}!\n"
            "Чтобы начать пользоваться VPN, оплати подписку",
            reply_markup=await free_user_kb(message.from_user.id),
        )

    await bot.send_message(
        message.from_user.id,
        "Подробное описание бота и его функционала доступно на"
        f" {hlink('странице', 'https://telegra.ph/FAQ-po-botu-05-18')}, оплачивая подписку, вы"
        " соглашаетесь с правилами использования бота и условиями возврата средств, указанными в"
        " статье выше.",
        parse_mode=ParseMode.HTML,
    )

    for admin in settings.ADMINS:
        await bot.send_message(
            admin,
            f"Новый пользователь: {hcode(message.from_user.full_name)}\n"
            f"id: {hcode(message.from_user.id)}, username: {hcode(message.from_user.username)}",
            parse_mode=ParseMode.HTML,
        )


@router.message(F.text == "💵 Оплатить")
async def choose_plan_handler(message: types.Message):
    await message.answer("Выберите тарифный план:", reply_markup=await get_plan_buttons())


@router.callback_query(F.data.startswith("choose_plan:"))
async def selected_plan_handler(callback: types.CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split(":")[1])
    await state.set_state(NewPayment.waiting_for_screenshot)
    await state.update_data(selected_plan_id=plan_id)
    plan = await sync_to_async(lambda: Plan.objects.get(id=plan_id))()

    message_text = (
        f"✅ Вы выбрали тарифный план: <b>{plan.name}</b>\n\n"
        f"<b>Описание:</b> {plan.description}\n"
        f"<b>Цена:</b> {plan.price}₽\n"
        f"<b>Срок действия:</b> {plan.duration_days} дней\n\n"
        f"💳 Для оплаты переведите <b>{plan.price}₽</b> на карту:\n"
        f"<code>{settings.PAYMENT_PHONE}</code>\n\n"
        f"📸 После оплаты отправьте скриншот перевода для подтверждения."
    )

    await callback.message.answer(
        message_text,
        reply_markup=await cancel_payment_kb(),
        parse_mode="HTML"
    )

    await callback.answer()



@router.message(NewPayment.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_id = data["selected_plan_id"]
    plan = await sync_to_async(lambda: Plan.objects.get(id=plan_id))()
    user = await sync_to_async(lambda: TgUser.objects.get(user_id=message.from_user.id))()

    purchase = await sync_to_async(Purchase.objects.create)(
        user=user,
        user_plan=plan,
        amount_paid=plan.price,
        successful=False
    )

    for admin_id in settings.ADMINS:
        await bot.send_photo(
            chat_id=admin_id,
            photo=message.photo[-1].file_id,
            caption=(
                f"🧾 Новый платёж\n\n"
                f"👤 Пользователь: {user.username} (ID: {user.user_id})\n"
                f"💳 Тариф: {plan.name}\n"
                f"💰 Сумма: {plan.price}₽\n"
                f"📆 Срок: {plan.duration_days} дней"
            ),
            reply_markup=confirm_payment_kb(purchase.id)
        )

    await message.answer("Скриншот получен, ожидайте подтверждения от администратора.")
    await message.answer("🔙 Вернуться в меню?", reply_markup=back_to_main_menu_kb())
    await state.clear()


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Оплата отменена.", reply_markup=None)
    await callback.answer()  # убрать статус ожидания колбека


@router.message(lambda msg: msg.text == "🕑 Моя подписка")
async def show_subscription_info(message: types.Message):
    user_id = message.from_user.id

    try:
        tg_user = await TgUser.objects.aget(user_id=user_id)
    except TgUser.DoesNotExist:
        await message.answer("❌ Вы не зарегистрированы в системе.")
        return

    if not tg_user.subscription_end_date or tg_user.subscription_end_date <= timezone.now():
        await message.answer("🔕 У вас нет активной подписки.")
        return

    # Получаем текущую успешную покупку
    latest_purchase = await tg_user.purchases.filter(successful=True).select_related("user_plan").order_by(
        "-created_at").afirst()

    left_days = (tg_user.subscription_end_date - timezone.now()).days

    if latest_purchase:
        plan = latest_purchase.user_plan
        await message.answer(
            f"🕑 Ваша подписка:\n\n"
            f"📦 План: <b>{plan.name}</b>\n"
            f"💰 Оплата: {latest_purchase.amount_paid}₽\n"
            f"⏳ Действует до: <b>{tg_user.subscription_end_date.strftime('%d.%m.%Y')}</b>\n"
            f"🗓 Осталось дней: {left_days}\n",
            parse_mode="HTML"
        )
        await message.answer("🔙 Вернуться в меню?", reply_markup=back_to_main_menu_kb())
    elif tg_user.is_trial_used:
        await message.answer(
            f"🧪 Ваша пробная подписка:\n\n"
            f"📦 План: <b>Пробный доступ</b>\n"
            f"💰 Оплата: 0₽\n"
            f"⏳ Действует до: <b>{tg_user.subscription_end_date.strftime('%d.%m.%Y')}</b>\n"
            f"🗓 Осталось дней: {left_days}\n",
            parse_mode="HTML"
        )
        await message.answer("🔙 Вернуться в меню?", reply_markup=back_to_main_menu_kb())
    else:
        await message.answer("🔕 У вас нет активной подписки.")


@router.message(F.text == "📁 Мои конфиги")
async def show_user_configs(message: types.Message):
    keyboard = await get_user_configs_kb(message.from_user.id)
    await message.answer("Ваши конфиги:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("get_config:"))
async def send_config_file(callback: CallbackQuery):
    config_id = int(callback.data.split(":")[1])
    try:
        config = await VpnClient.objects.select_related("user").aget(id=config_id)
    except VpnClient.DoesNotExist:
        await callback.message.answer("❌ Конфигурация не найдена.")
        return

    if config.user.user_id != callback.from_user.id:
        await callback.message.answer("❌ У вас нет доступа к этому конфигу.")
        return

    # Скачиваем файл и QR
    config_path = await download_config_file(config.wg_id)
    qr_code_path = await get_qr_code(config.wg_id)

    await callback.message.answer_document(
        document=FSInputFile(config_path, filename=f"{config.config_name}.conf"),
        caption=f"Конфигурация: {config.config_name}"
    )
    await callback.message.answer_photo(
        photo=FSInputFile(qr_code_path),
        caption="QR-код для быстрой настройки"
    )
    await callback.answer()


@router.callback_query(F.data == "create_config")
async def ask_config_name(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_id(callback.from_user.id)

    if not user or not user.has_active_subscription():
        await callback.message.answer("❌ У вас нет активной подписки.")
        await callback.answer()
        return

    await callback.message.answer("📝 Введите имя для новой конфигурации:")
    await state.set_state(NewConfig.waiting_for_config_name)
    await callback.answer()


@router.message(NewConfig.waiting_for_config_name)
async def process_config_name(message: Message, state: FSMContext):
    device_name = message.text.strip()

    if len(device_name) < 3 or len(device_name) > 30:
        await message.answer("⚠️ Имя должно быть от 3 до 30 символов. Попробуйте снова.")
        return

    user = await get_user_by_id(message.from_user.id)

    if not user or not user.has_active_subscription():
        await message.answer("❌ У вас нет активной подписки.")
        await state.clear()
        return

    # 🔒 Проверка лимита устройств по тарифу
    from asgiref.sync import sync_to_async

    @sync_to_async
    def is_limit_reached(user):
        latest_purchase = user.purchases.filter(successful=True).select_related("user_plan").order_by(
            "-created_at").first()
        if not latest_purchase:
            return True  # если нет активного плана, запретить создание
        plan = latest_purchase.user_plan
        return VpnClient.objects.filter(user=user, active=True).count() >= plan.max_devices

    if await is_limit_reached(user):
        await message.answer("❗ Вы достигли лимита устройств по вашему тарифному плану.")
        await state.clear()
        return

    # Проверим, есть ли уже конфиг с таким именем
    exists = await sync_to_async(VpnClient.objects.filter(user=user, config_name=device_name).exists)()
    if exists:
        await message.answer("⚠️ Конфигурация с таким именем уже существует. Введите другое имя.")
        return

    # Генерация и отправка конфига
    config_text = await issue_vpn_config(user, device_name)
    if not config_text:
        await message.answer("⚠️ Ошибка при получении конфигурации.")
        return

    config_bytes = config_text.encode()
    config_file = BufferedInputFile(config_bytes, filename=f"{device_name}.conf")

    from app_bot.keyboards.inline import get_user_configs_kb

    await message.answer_document(
        document=config_file,
        caption=f"✅ Конфигурация <b>{device_name}</b> создана.",
        reply_markup=await get_user_configs_kb(user.user_id),
        parse_mode="HTML"
    )

    await state.clear()


@router.message(F.text == "📝 Помощь")
async def cmd_support(message: Message):
    # Ссылка на Telegra.ph
    await message.answer(
        f"📄 Подробное описание бота и его функционала доступно на {hlink('странице', 'https://telegra.ph/FAQ-po-botu-05-18')}",
        parse_mode="HTML",
    )

    admin_id = settings.ADMINS[0] if settings.ADMINS else None

    if admin_id:
        admin_user = await get_user_by_id(admin_id)
        if admin_user and admin_user.username:
            admin_link = f"https://t.me/{admin_user.username}"
            await message.answer(
                f"❓ Если у тебя всё ещё остались вопросы, напиши {hlink('мне', admin_link)} лично.",
                parse_mode="HTML",
            )
        else:
            await message.answer("❗ Не удалось найти username администратора.")
    else:
        await message.answer("❗ Администратор не задан в настройках.")

    await message.answer("🔙 Вернуться в меню?", reply_markup=back_to_main_menu_kb())


@router.message(F.text == "🔙 Назад")
async def go_back_to_main_menu(message: Message):
    from app_vpn.models import TgUser
    user_id = message.from_user.id

    if await is_user_payed(user_id):
        keyboard = await payed_user_kb()
    else:
        keyboard = await free_user_kb(user_id=user_id)

    await message.answer("🔘 Главное меню:", reply_markup=keyboard)


@router.message(F.text == "💳 Тарифы")
async def show_tariffs(message: Message):
    kb = await get_plan_buttons()
    await message.answer("💳 Выберите тариф:", reply_markup=kb)
