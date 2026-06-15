"""
handlers/orders.py — Чеки и история заказов.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import Database
from utils.helpers import format_receipts
from utils.keyboards import main_menu_kb

router = Router()


@router.callback_query(F.data == "menu:orders")
async def show_orders(call: CallbackQuery, db: Database):
    user = db.get_user(call.from_user.id)
    if not user:
        await call.answer("Сначала напиши /start.", show_alert=True)
        return

    orders = db.get_user_orders(call.from_user.id)
    text = format_receipts(user, orders)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"))

    await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()