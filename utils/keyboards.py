"""
utils/keyboards.py — Все клавиатуры бота.
"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📋 Прайс", callback_data="menu:price"))
    kb.row(InlineKeyboardButton(text="🧾 Чеки / Мои заказы", callback_data="menu:orders"))
    kb.row(InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu:support"))
    return kb.as_markup()


def categories_kb(categories: list, cart_count: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.row(InlineKeyboardButton(
            text=cat["name"],
            callback_data=f"cat:{cat['id']}"
        ))
    row = []
    if cart_count > 0:
        row.append(InlineKeyboardButton(
            text=f"🛒 Корзина ({cart_count})",
            callback_data="cart:view"
        ))
    row.append(InlineKeyboardButton(text="🚫 Отменить 🚫", callback_data="cart:cancel"))
    kb.row(*row)
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"))
    return kb.as_markup()


def items_kb(items: list, cat_id: str, cart_ids: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        in_cart = "✅ " if item["id"] in cart_ids else ""
        kb.row(InlineKeyboardButton(
            text=f"{in_cart}{item['name']} — {item['price']}₽",
            callback_data=f"item:{item['id']}"
        ))
    row = []
    if cart_ids:
        row.append(InlineKeyboardButton(
            text=f"🛒 Корзина ({len(cart_ids)})",
            callback_data="cart:view"
        ))
    row.append(InlineKeyboardButton(text="🚫 Отменить 🚫", callback_data="cart:cancel"))
    kb.row(*row)
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="price:back"))
    return kb.as_markup()


def item_detail_kb(item_id: str, in_cart: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if in_cart:
        kb.row(InlineKeyboardButton(
            text="❌ Убрать из корзины",
            callback_data=f"cart:remove:{item_id}"
        ))
    else:
        kb.row(InlineKeyboardButton(
            text="✅ Добавить в корзину",
            callback_data=f"cart:add:{item_id}"
        ))
    kb.row(InlineKeyboardButton(text="🚫 Отменить 🚫", callback_data="cart:cancel"))
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"item:back:{item_id}"))
    return kb.as_markup()


def cart_kb(has_items: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_items:
        kb.row(InlineKeyboardButton(text="✅ Оформить заказ", callback_data="cart:checkout"))
    kb.row(InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart:clear"))
    kb.row(InlineKeyboardButton(text="🚫 Отменить 🚫", callback_data="cart:cancel"))
    kb.row(InlineKeyboardButton(text="◀️ Продолжить выбор", callback_data="menu:price"))
    return kb.as_markup()


def payment_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="1️⃣ Рубли (₽)", callback_data="pay:1"))
    kb.row(InlineKeyboardButton(text="2️⃣ Звёзды Тг (⭐) +15%", callback_data="pay:2"))
    kb.row(InlineKeyboardButton(text="3️⃣ Другая валюта 💳 +10%", callback_data="pay:3"))
    kb.row(InlineKeyboardButton(text="🚫 Отменить 🚫", callback_data="cart:cancel"))
    return kb.as_markup()


def confirm_success_kb(order_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="✅ Да, подтверждаю",
        callback_data=f"success:confirm:{order_id}"
    ))
    kb.row(InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cart:cancel"))
    return kb.as_markup()


def review_skip_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Пропустить отзыв", callback_data="review:skip"))
    return kb.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"))
    kb.row(InlineKeyboardButton(text="📋 Редактор прайса", callback_data="admin:price"))
    kb.row(InlineKeyboardButton(text="👥 Список админов", callback_data="admin:admins"))
    kb.row(InlineKeyboardButton(text="🔗 Привязать супергруппу", callback_data="admin:bindgroup"))
    kb.row(InlineKeyboardButton(text="✏️ Изменить текст приветствия", callback_data="admin:edit_welcome"))
    kb.row(InlineKeyboardButton(text="✏️ Изменить текст прайса", callback_data="admin:edit_price_text"))
    kb.row(InlineKeyboardButton(text="🆘 Изменить ссылку поддержки", callback_data="admin:edit_support"))
    return kb.as_markup()


def admin_price_kb(categories: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.row(InlineKeyboardButton(
            text=f"📁 {cat['name']}",
            callback_data=f"admin:cat:{cat['id']}"
        ))
    kb.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:add_cat"))
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back"))
    return kb.as_markup()


def admin_category_kb(cat_id: str, items: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.row(InlineKeyboardButton(
            text=f"🔧 {item['name']} — {item['price']}₽",
            callback_data=f"admin:item:{item['id']}"
        ))
    kb.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"admin:add_item:{cat_id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"admin:del_cat:{cat_id}"))
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:price"))
    return kb.as_markup()


def admin_item_kb(item_id: str, cat_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"admin:edit_item_name:{item_id}"))
    kb.row(InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"admin:edit_item_price:{item_id}"))
    kb.row(InlineKeyboardButton(text="📦 Изменить минимум", callback_data=f"admin:edit_item_min:{item_id}"))
    kb.row(InlineKeyboardButton(text="💳 Изменить способы оплаты", callback_data=f"admin:edit_item_pay:{item_id}"))
    kb.row(InlineKeyboardButton(text="🎯 Изменить подсказку (target)", callback_data=f"admin:edit_item_hint:{item_id}"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"admin:del_item:{item_id}"))
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin:cat:{cat_id}"))
    return kb.as_markup()


def remove_kb():
    return ReplyKeyboardRemove()