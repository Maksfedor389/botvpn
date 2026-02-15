from __future__ import annotations

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import (
    ADMIN_IDS,
    BOT_TOKEN,
    PAYMENT_PHONE,
    PLANS,
    XRAY_ACCESS_TEMPLATE,
    DB_PATH,
    THREEXUI_BASE_URL,
    THREEXUI_INBOUND_ID,
    THREEXUI_PASSWORD,
    THREEXUI_USERNAME,
    validate_settings,
)
from db import Database
from three_xui import ThreeXUI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database(DB_PATH)
xui = ThreeXUI(THREEXUI_BASE_URL, THREEXUI_USERNAME, THREEXUI_PASSWORD, THREEXUI_INBOUND_ID)

WAITING_PHONE, WAITING_RECEIPT = range(2)


def plans_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for p in PLANS.values():
        rows.append([InlineKeyboardButton(f"{p.title} — {p.price_rub}₽", callback_data=f"buy:{p.code}")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "Выберите подписку на VPN:"
    await update.message.reply_text(text, reply_markup=plans_keyboard())
    return ConversationHandler.END


async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, plan_code = query.data.split(":", 1)
    if plan_code not in PLANS:
        await query.message.reply_text("Неизвестный тариф.")
        return ConversationHandler.END

    context.user_data["plan_code"] = plan_code
    contact_btn = KeyboardButton("Отправить номер", request_contact=True)
    kb = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    await query.message.reply_text("Отправьте ваш номер телефона для оформления заказа.", reply_markup=kb)
    return WAITING_PHONE


async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    if not phone:
        await update.message.reply_text("Не удалось получить номер. Повторите.")
        return WAITING_PHONE

    plan = PLANS[context.user_data["plan_code"]]
    order_id = db.create_order(
        user_id=update.effective_user.id,
        username=update.effective_user.username or "",
        plan_code=plan.code,
        amount_rub=plan.price_rub,
        phone=phone,
    )
    context.user_data["order_id"] = order_id

    await update.message.reply_text(
        (
            f"Заказ #{order_id} создан.\n"
            f"Тариф: {plan.title}\n"
            f"Сумма к оплате: {plan.price_rub}₽\n\n"
            f"Сделайте перевод на номер: {PAYMENT_PHONE}\n"
            "После оплаты отправьте скриншот чека, файл или текст с деталями перевода."
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_RECEIPT


async def receipt_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    order_id = context.user_data.get("order_id")
    if not order_id:
        await update.message.reply_text("Заказ не найден. Нажмите /start")
        return ConversationHandler.END

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id

    note = update.message.caption or update.message.text or ""
    db.set_receipt(order_id, file_id=file_id, note=note)

    order = db.get_order(order_id)
    if not order:
        await update.message.reply_text("Ошибка сохранения заказа.")
        return ConversationHandler.END

    action_kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_approve:{order.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject:{order.id}"),
        ]]
    )

    admin_text = (
        f"🧾 Новая заявка #{order.id}\n"
        f"Пользователь: @{order.username or 'без_username'} (id={order.user_id})\n"
        f"Тариф: {order.plan_code}\n"
        f"Сумма: {order.amount_rub}₽\n"
        f"Телефон клиента: {order.phone}\n"
        f"Комментарий: {order.receipt_note or '-'}"
    )

    for admin_id in ADMIN_IDS:
        if file_id:
            await context.bot.send_photo(admin_id, photo=file_id, caption=admin_text, reply_markup=action_kb)
        else:
            await context.bot.send_message(admin_id, admin_text, reply_markup=action_kb)

    await update.message.reply_text("Чек получен. Ожидайте подтверждения администратора.")
    return ConversationHandler.END


async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.message.reply_text("Недостаточно прав.")
        return

    action, order_id_s = query.data.split(":", 1)
    order = db.get_order(int(order_id_s))
    if not order:
        await query.message.reply_text("Заказ не найден.")
        return

    if action == "admin_reject":
        db.set_order_status(order.id, "rejected")
        await context.bot.send_message(order.user_id, f"Заказ #{order.id} отклонен. Свяжитесь с поддержкой.")
        await query.edit_message_reply_markup(None)
        return

    if action != "admin_approve":
        return

    plan = PLANS[order.plan_code]
    try:
        client = xui.create_client(order.user_id, days=plan.duration.days)
    except Exception as exc:
        logger.exception("Ошибка выдачи подписки")
        await query.message.reply_text(f"Ошибка в 3x-ui: {exc}")
        return

    db.set_order_status(order.id, "approved")
    db.add_subscription(
        user_id=order.user_id,
        order_id=order.id,
        plan_code=order.plan_code,
        uuid=client.uuid,
        email=client.email,
        expires_at=client.expiry_date.isoformat(),
    )

    access_text = XRAY_ACCESS_TEMPLATE.format(
        uuid=client.uuid,
        email=client.email,
        expiry_date=client.expiry_date.strftime("%Y-%m-%d"),
    )
    await context.bot.send_message(order.user_id, access_text)

    await query.edit_message_reply_markup(None)
    await query.message.reply_text(f"Заказ #{order.id} подтвержден и выдан.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main() -> None:
    validate_settings()
    application = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(buy_plan, pattern=r"^buy:")],
        states={
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), phone_received),
            ],
            WAITING_RECEIPT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), receipt_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv)
    application.add_handler(CallbackQueryHandler(admin_action, pattern=r"^admin_(approve|reject):"))

    application.run_polling()


if __name__ == "__main__":
    main()
