"""
handlers/admin.py — Админ-панель.
Доступна только пользователям из ADMIN_IDS.
"""

import uuid
import config
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from database import Database
from utils.keyboards import (
    admin_menu_kb, admin_price_kb, admin_category_kb, admin_item_kb
)

router = Router()


# ─── FSM для редактирования ──────────────────────────────────────────────────

class AdminState(StatesGroup):
    edit_welcome = State()
    edit_price_text = State()
    edit_support = State()
    add_cat_name = State()
    add_item_cat = State()
    add_item_name = State()
    add_item_price = State()
    add_item_min = State()
    add_item_pay = State()
    add_item_hint = State()
    add_item_has_target = State()
    edit_item_field = State()
    edit_item_field_value = State()
    pending_cat_id = State()
    pending_item_id = State()
    pending_edit_field = State()
    pending_new_item = State()


# ─── Проверка прав ───────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    config.reload_config()
    return user_id in config.ADMIN_IDS


# ─── /admin ──────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")
    await call.answer()


# ─── Статистика ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return

    users = db.get_all_users()
    orders = db.get_all_orders()

    total_users = len(users)
    total_orders = len(orders)
    done = sum(1 for o in orders.values() if o["status"] == "done")
    cancelled = sum(1 for o in orders.values() if o["status"] == "cancelled")
    active = sum(1 for o in orders.values() if o["status"] == "active")
    total_revenue = sum(o["total_rub"] for o in orders.values() if o["status"] == "done")

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back"))

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Запустили бота: <b>{total_users}</b>\n\n"
        f"📦 Всего заказов: <b>{total_orders}</b>\n"
        f"  ✅ Выполнено: <b>{done}</b>\n"
        f"  ⏳ Активных: <b>{active}</b>\n"
        f"  ❌ Отменено: <b>{cancelled}</b>\n\n"
        f"💰 Общая выручка: <b>{total_revenue:.0f}₽</b>"
    )

    await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()


# ─── Список админов ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:admins")
async def admin_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    config.reload_config()
    ids = config.ADMIN_IDS
    text = "👥 <b>Список администраторов:</b>\n\n"
    for i, uid in enumerate(ids, 1):
        text += f"{i}. <code>{uid}</code>\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back"))

    await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()


# ─── Привязка супергруппы ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:bindgroup")
async def bind_group_prompt(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    current = config.GROUP_ID
    text = (
        "🔗 <b>Привязка супергруппы</b>\n\n"
        f"Текущая группа: <code>{current or 'не привязана'}</code>\n\n"
        "Добавь бота в супергруппу с форумом (топиками), сделай его администратором, "
        "затем перешли мне любое сообщение из этой группы или напиши её ID командой:\n"
        "<code>/bindgroup -100XXXXXXXXXX</code>"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back"))
    await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()


@router.message(Command("bindgroup"))
async def cmd_bindgroup(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /bindgroup -100XXXXXXXXXX")
        return
    group_id_str = parts[1]
    if not group_id_str.lstrip("-").isdigit():
        await message.answer("❌ Неверный формат ID.")
        return
    gid = int(group_id_str)
    config.save_config(GROUP_ID=gid)
    await message.answer(f"✅ Супергруппа <code>{gid}</code> привязана!", parse_mode="HTML")


# ─── Редактирование текстов ──────────────────────────────────────────────────

@router.callback_query(F.data == "admin:edit_welcome")
async def edit_welcome_prompt(call: CallbackQuery, db: Database, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    current = db.get_setting("welcome_text", "")
    await call.message.answer(
        f"✏️ Текущий текст приветствия:\n\n{current}\n\n"
        "Отправь новый текст (можно использовать {name} для имени пользователя, HTML-теги):"
    )
    await state.set_state(AdminState.edit_welcome)
    await call.answer()


@router.message(AdminState.edit_welcome)
async def save_welcome(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    db.set_setting("welcome_text", message.text)
    await state.clear()
    await message.answer("✅ Текст приветствия обновлён!", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:edit_price_text")
async def edit_price_text_prompt(call: CallbackQuery, db: Database, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    current = db.get_setting("price_text", "")
    await call.message.answer(
        f"✏️ Текущий текст прайса:\n\n{current}\n\n"
        "Отправь новый текст:"
    )
    await state.set_state(AdminState.edit_price_text)
    await call.answer()


@router.message(AdminState.edit_price_text)
async def save_price_text(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    db.set_setting("price_text", message.text)
    await state.clear()
    await message.answer("✅ Текст прайса обновлён!", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:edit_support")
async def edit_support_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(
        f"✏️ Текущая ссылка поддержки: {config.SUPPORT_LINK}\n\n"
        "Отправь новый @username или ссылку:"
    )
    await state.set_state(AdminState.edit_support)
    await call.answer()


@router.message(AdminState.edit_support)
async def save_support(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    config.save_config(SUPPORT_LINK=message.text.strip())
    await state.clear()
    await message.answer("✅ Ссылка поддержки обновлена!", reply_markup=admin_menu_kb())


# ─── Редактор прайса ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:price")
async def admin_price(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    price = db.get_price()
    price_json = str(price).replace("'", '"')[:500]
    await call.message.edit_text(
        "📋 <b>Редактор прайса</b>\n\nВыбери категорию для редактирования:",
        reply_markup=admin_price_kb(price["categories"]),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:cat:"))
async def admin_category(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    cat_id = call.data.split(":", 2)[2]
    cat = db.get_category(cat_id)
    if not cat:
        await call.answer("Не найдено.", show_alert=True)
        return

    text = f"📁 <b>{cat['name']}</b>\n\nТовары в категории:"
    if not cat["items"]:
        text += "\n— пусто"

    await call.message.edit_text(
        text,
        reply_markup=admin_category_kb(cat_id, cat["items"]),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "admin:add_cat")
async def add_cat_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("📁 Введи название новой категории (с эмодзи):")
    await state.set_state(AdminState.add_cat_name)
    await call.answer()


@router.message(AdminState.add_cat_name)
async def save_new_cat(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    cat_id = f"cat_{uuid.uuid4().hex[:6]}"
    db.add_category(cat_id, message.text.strip())
    await state.clear()
    price = db.get_price()
    await message.answer(
        "✅ Категория добавлена!",
        reply_markup=admin_price_kb(price["categories"])
    )


@router.callback_query(F.data.startswith("admin:del_cat:"))
async def del_cat(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    cat_id = call.data.split(":", 2)[2]
    db.delete_category(cat_id)
    price = db.get_price()
    await call.message.edit_text(
        "✅ Категория удалена.\n\n📋 <b>Редактор прайса</b>",
        reply_markup=admin_price_kb(price["categories"]),
        parse_mode="HTML"
    )
    await call.answer("Удалено.")


@router.callback_query(F.data.startswith("admin:add_item:"))
async def add_item_prompt(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    cat_id = call.data.split(":", 2)[2]
    await state.update_data(pending_cat_id=cat_id, pending_new_item={})
    await call.message.answer("✏️ Введи название товара (с эмодзи):")
    await state.set_state(AdminState.add_item_name)
    await call.answer()


@router.message(AdminState.add_item_name)
async def add_item_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    item = data.get("pending_new_item", {})
    item["name"] = message.text.strip()
    await state.update_data(pending_new_item=item)
    await message.answer("💰 Введи цену за 1 ед. (только число):")
    await state.set_state(AdminState.add_item_price)


@router.message(AdminState.add_item_price)
async def add_item_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().replace(".", "").isdigit():
        await message.answer("❌ Только число. Попробуй ещё:")
        return
    data = await state.get_data()
    item = data.get("pending_new_item", {})
    item["price"] = float(message.text.strip())
    await state.update_data(pending_new_item=item)
    await message.answer("📦 Введи минимальное количество:")
    await state.set_state(AdminState.add_item_min)


@router.message(AdminState.add_item_min)
async def add_item_min(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().isdigit():
        await message.answer("❌ Только целое число:")
        return
    data = await state.get_data()
    item = data.get("pending_new_item", {})
    item["min_qty"] = int(message.text.strip())
    await state.update_data(pending_new_item=item)
    await message.answer("💳 Способы оплаты (через запятую, например: 1,2,3):\n1=₽, 2=⭐, 3=💳")
    await state.set_state(AdminState.add_item_pay)


@router.message(AdminState.add_item_pay)
async def add_item_pay(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    item = data.get("pending_new_item", {})
    item["payment_types"] = message.text.strip()
    await state.update_data(pending_new_item=item)
    await message.answer(
        "🎯 Нужно ли указывать цель (например @user для звёзд)?\n"
        "Если да — напиши подсказку (например: 'Укажи @user для звёзд')\n"
        "Если нет — напиши '-'"
    )
    await state.set_state(AdminState.add_item_hint)


@router.message(AdminState.add_item_hint)
async def add_item_hint(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    item = data.get("pending_new_item", {})
    hint = message.text.strip()
    if hint == "-":
        item["target_hint"] = ""
        item["has_target"] = False
    else:
        item["target_hint"] = hint
        item["has_target"] = True

    item["id"] = f"item_{uuid.uuid4().hex[:6]}"
    cat_id = data.get("pending_cat_id")
    db.add_item(cat_id, item)

    await state.clear()
    cat = db.get_category(cat_id)
    await message.answer(
        f"✅ Товар <b>{item['name']}</b> добавлен!",
        reply_markup=admin_category_kb(cat_id, cat["items"] if cat else []),
        parse_mode="HTML"
    )


# ─── Редактирование товара ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin:item:"))
async def admin_item(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    item_id = call.data.split(":", 2)[2]
    item = db.get_item(item_id)
    if not item:
        await call.answer("Не найдено.", show_alert=True)
        return

    # Найти категорию
    price = db.get_price()
    cat_id = ""
    for cat in price["categories"]:
        for it in cat["items"]:
            if it["id"] == item_id:
                cat_id = cat["id"]

    text = (
        f"🔧 <b>Редактирование: {item['name']}</b>\n\n"
        f"💰 Цена: {item['price']}₽\n"
        f"📦 Минимум: {item['min_qty']} ед.\n"
        f"💳 Оплата: {item.get('payment_types','1,2,3')}\n"
        f"🎯 Подсказка: {item.get('target_hint') or '—'}\n"
    )
    await call.message.edit_text(text, reply_markup=admin_item_kb(item_id, cat_id), parse_mode="HTML")
    await call.answer()


def _edit_item_state_handler(field: str, prompt: str):
    """Фабрика: создаёт пару (callback, message) для редактирования поля товара."""

    async def on_callback(call: CallbackQuery, state: FSMContext):
        if not is_admin(call.from_user.id):
            return
        item_id = call.data.split(":", 3)[3]
        await state.update_data(pending_item_id=item_id, pending_edit_field=field)
        await call.message.answer(prompt)
        await state.set_state(AdminState.edit_item_field_value)
        await call.answer()

    return on_callback


# Регистрируем редакторы полей
for _cb, _field, _prompt in [
    ("admin:edit_item_name:", "name", "✏️ Введи новое название товара:"),
    ("admin:edit_item_price:", "price", "💰 Введи новую цену (число):"),
    ("admin:edit_item_min:", "min_qty", "📦 Введи новый минимум (целое число):"),
    ("admin:edit_item_pay:", "payment_types", "💳 Введи способы оплаты (1,2,3):"),
    ("admin:edit_item_hint:", "target_hint", "🎯 Введи новую подсказку (или '-' для удаления):"),
]:
    router.callback_query(F.data.startswith(_cb))(_edit_item_state_handler(_field, _prompt))


@router.message(AdminState.edit_item_field_value)
async def save_item_field(message: Message, db: Database, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    item_id = data.get("pending_item_id")
    field = data.get("pending_edit_field")

    value = message.text.strip()
    if field in ("price",):
        if not value.replace(".", "").isdigit():
            await message.answer("❌ Введи число:")
            return
        value = float(value)
    elif field in ("min_qty",):
        if not value.isdigit():
            await message.answer("❌ Введи целое число:")
            return
        value = int(value)
    elif field == "target_hint" and value == "-":
        value = ""

    db.update_item(item_id, **{field: value})
    await state.clear()

    item = db.get_item(item_id)
    price = db.get_price()
    cat_id = ""
    for cat in price["categories"]:
        for it in cat["items"]:
            if it["id"] == item_id:
                cat_id = cat["id"]

    await message.answer(
        f"✅ Поле обновлено!",
        reply_markup=admin_item_kb(item_id, cat_id)
    )


@router.callback_query(F.data.startswith("admin:del_item:"))
async def del_item(call: CallbackQuery, db: Database):
    if not is_admin(call.from_user.id):
        return
    item_id = call.data.split(":", 2)[2]

    price = db.get_price()
    cat_id = ""
    for cat in price["categories"]:
        for it in cat["items"]:
            if it["id"] == item_id:
                cat_id = cat["id"]

    db.delete_item(item_id)
    cat = db.get_category(cat_id) if cat_id else None

    await call.message.edit_text(
        "✅ Товар удалён.",
        reply_markup=admin_category_kb(cat_id, cat["items"] if cat else [])
    )
    await call.answer("Удалено.")