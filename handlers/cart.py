"""
handlers/cart.py — Корзина, оформление заказа, пересылка в группу.
"""

import config
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from database import Database
from utils.keyboards import cart_kb, payment_kb, confirm_success_kb, review_skip_kb, main_menu_kb
from utils.helpers import format_cart_text, format_order_message, calc_total, PAYMENT_NAMES

router = Router()


class OrderState(StatesGroup):
    waiting_message = State()   # ждём доп. сообщение от заказчика
    waiting_review = State()    # ждём отзыв
    confirm_success = State()   # подтверждение выполнения


def get_cart(data: dict) -> list:
    return data.get("cart", [])


@router.callback_query(F.data == "cart:view")
async def view_cart(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(data)
    text = format_cart_text(cart)
    await call.message.answer(text, reply_markup=cart_kb(bool(cart)), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "cart:clear")
async def clear_cart(call: CallbackQuery, state: FSMContext):
    await state.update_data(cart=[])
    await call.message.edit_text("🗑 Корзина очищена.", reply_markup=cart_kb(False))
    await call.answer("Корзина очищена.")


@router.callback_query(F.data == "cart:cancel")
async def cancel_cart(call: CallbackQuery, state: FSMContext, db: Database):
    await state.clear()
    welcome = db.get_setting("welcome_text",
        "👋 Привет, {name}!\n\nДобро пожаловать! Выбери нужный раздел ниже 👇")
    text = welcome.replace("{name}", call.from_user.first_name)
    await call.message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await call.answer("Отменено.")


@router.callback_query(F.data == "cart:checkout")
async def checkout(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(data)
    if not cart:
        await call.answer("Корзина пуста!", show_alert=True)
        return

    text = format_cart_text(cart)
    await call.message.answer(
        f"{text}\n\n💳 Выбери способ оплаты:",
        reply_markup=payment_kb(),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay:"))
async def choose_payment(call: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    pay_type = int(call.data.split(":")[1])
    data = await state.get_data()
    cart = get_cart(data)

    if not cart:
        await call.answer("Корзина пуста!", show_alert=True)
        return

    total_rub, total_final, total_display = calc_total(cart, pay_type)
    await state.update_data(payment_type=pay_type, total_rub=total_rub, total_display=total_display)

    # Создаём заказ в БД
    order_id = db.create_order(
        user_id=call.from_user.id,
        cart=cart,
        payment_type=pay_type,
        total_rub=total_rub,
        total_display=total_display,
    )
    await state.update_data(current_order_id=order_id)

    # Отправляем в супергруппу
    group_id = config.GROUP_ID
    user_data = db.get_user(call.from_user.id)

    if group_id and user_data:
        order_text = format_order_message(user_data, cart, pay_type, total_rub, total_display)
        try:
            # Создаём топик для пользователя (если нет)
            topic_id = db.get_topic(call.from_user.id)
            if not topic_id:
                uname = user_data.get("username") or str(user_data["id"])
                forum_topic = await bot.create_forum_topic(
                    chat_id=group_id,
                    name=f"{user_data['first_name']} (@{uname})"
                )
                topic_id = forum_topic.message_thread_id
                db.set_topic(call.from_user.id, topic_id)

            sent = await bot.send_message(
                chat_id=group_id,
                message_thread_id=topic_id,
                text=order_text,
                parse_mode="HTML"
            )
            db.update_order(order_id, topic_id=topic_id)
        except TelegramBadRequest as e:
            # Если топики не поддерживаются — шлём без них
            try:
                sent = await bot.send_message(
                    chat_id=group_id,
                    text=order_text,
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # Просим заказчика написать доп. сообщение
    cart_summary = format_cart_text(cart, pay_type)
    await call.message.answer(
        f"✅ Заказ оформлен!\n\n{cart_summary}\n\n"
        f"💬 Напиши дополнительное сообщение для продавца "
        f"(уточнения, пожелания и т.д.).\n\n"
        f"Дальнейшие сообщения будут пересылаться продавцу для обсуждения заказа и получения реквизитов.\n"
        f"⏳ Продавец не всегда отвечает сразу — просим терпения.\n\n"
        f"Команда /stop — отменить заказ.",
        parse_mode="HTML"
    )
    await state.set_state(OrderState.waiting_message)
    await call.answer()


@router.message(OrderState.waiting_message)
async def forward_user_message(message: Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    order_id = data.get("current_order_id")
    if not order_id:
        return

    order = db.get_order(order_id)
    if not order:
        return

    group_id = config.GROUP_ID
    topic_id = order.get("topic_id") or db.get_topic(message.from_user.id)

    if group_id and topic_id:
        try:
            # Пересылаем анонимно — копируем текст/медиа без ссылки на юзера
            if message.text:
                await bot.send_message(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    text=f"📨 <i>Сообщение от заказчика:</i>\n{message.text}",
                    parse_mode="HTML"
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    photo=message.photo[-1].file_id,
                    caption=f"📨 <i>Медиа от заказчика</i>\n{message.caption or ''}",
                    parse_mode="HTML"
                )
            elif message.document:
                await bot.send_document(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    document=message.document.file_id,
                    caption=f"📨 <i>Файл от заказчика</i>",
                    parse_mode="HTML"
                )
            elif message.sticker:
                await bot.send_sticker(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    sticker=message.sticker.file_id
                )
        except Exception as e:
            pass

    await message.answer("📤 Сообщение доставлено продавцу.")


@router.message(F.text == "/stop")
async def stop_order(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    order_id = data.get("current_order_id")

    if order_id:
        db.cancel_order(order_id)

    await state.clear()
    await message.answer(
        "❌ Заказ отменён.",
        reply_markup=main_menu_kb()
    )


@router.message(F.text == "/success")
async def success_command(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    order_id = data.get("current_order_id")

    if not order_id:
        # Ищем активный заказ
        order = db.get_active_order(message.from_user.id)
        if order:
            order_id = order["id"]
            await state.update_data(current_order_id=order_id)
        else:
            await message.answer("У тебя нет активного заказа.")
            return

    await message.answer(
        "✅ Ты подтверждаешь, что заказ выполнен?\n\n"
        "Нажми ещё раз для подтверждения:",
        reply_markup=confirm_success_kb(order_id)
    )
    await state.set_state(OrderState.confirm_success)


@router.callback_query(F.data.startswith("success:confirm:"))
async def confirm_success(call: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    order_id = call.data.split(":", 2)[2]
    db.finish_order(order_id)

    await call.message.edit_text("✅ Заказ подтверждён как выполненный!")

    # Просим оставить отзыв
    await call.message.answer(
        "⭐ Пожалуйста, оставь отзыв о заказе!\n"
        "Можешь приложить фото/видео + текст или просто текст.",
        reply_markup=review_skip_kb()
    )
    await state.update_data(review_order_id=order_id)
    await state.set_state(OrderState.waiting_review)
    await call.answer()


@router.message(OrderState.waiting_review)
async def receive_review(message: Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    order_id = data.get("review_order_id") or data.get("current_order_id")
    order = db.get_order(order_id) if order_id else None

    group_id = config.GROUP_ID
    topic_id = (order.get("topic_id") if order else None) or db.get_topic(message.from_user.id)

    review_header = (
        f"⭐ <b>Отзыв от</b> {message.from_user.first_name} "
        f"(@{message.from_user.username or message.from_user.id})\n"
        f"Заказ: {order_id or '—'}\n\n"
    )

    if group_id and topic_id:
        try:
            if message.text:
                await bot.send_message(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    text=review_header + message.text,
                    parse_mode="HTML"
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=group_id,
                    message_thread_id=topic_id,
                    photo=message.photo[-1].file_id,
                    caption=review_header + (message.caption or ""),
                    parse_mode="HTML"
                )
        except Exception:
            pass

    await message.answer(
        "🙏 Спасибо за отзыв!",
        reply_markup=main_menu_kb()
    )
    await state.clear()


@router.callback_query(F.data == "review:skip")
async def skip_review(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Хорошо, отзыв пропущен. Спасибо за заказ! 🙏")
    await call.message.answer("Главное меню 👇", reply_markup=main_menu_kb())
    await call.answer()