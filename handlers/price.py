"""
handlers/price.py — Прайс, категории, просмотр товаров.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from utils.keyboards import categories_kb, items_kb, item_detail_kb
from utils.helpers import format_item_info

router = Router()


class CartState(StatesGroup):
    choosing_qty = State()
    choosing_target = State()
    pending_item_id = State()


def get_cart(state_data: dict) -> list:
    return state_data.get("cart", [])


def get_cart_ids(cart: list) -> list:
    return [i["id"] for i in cart]


@router.callback_query(F.data == "menu:price")
async def show_price(call: CallbackQuery, db: Database, state: FSMContext):
    price_text = db.get_setting("price_text", "📋 <b>Прайс-лист</b>\n\nВыбери категорию 👇")
    price = db.get_price()
    data = await state.get_data()
    cart = get_cart(data)

    await call.message.edit_text(
        price_text,
        reply_markup=categories_kb(price["categories"], len(cart)),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def show_category(call: CallbackQuery, db: Database, state: FSMContext):
    cat_id = call.data.split(":", 1)[1]
    cat = db.get_category(cat_id)
    if not cat:
        await call.answer("Категория не найдена.", show_alert=True)
        return

    data = await state.get_data()
    cart = get_cart(data)
    cart_ids = get_cart_ids(cart)

    await state.update_data(current_cat=cat_id)
    await call.message.edit_text(
        f"📁 <b>{cat['name']}</b>\n\nВыбери товар 👇",
        reply_markup=items_kb(cat["items"], cat_id, cart_ids),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "price:back")
async def price_back(call: CallbackQuery, db: Database, state: FSMContext):
    price_text = db.get_setting("price_text", "📋 <b>Прайс-лист</b>\n\nВыбери категорию 👇")
    price = db.get_price()
    data = await state.get_data()
    cart = get_cart(data)

    await call.message.edit_text(
        price_text,
        reply_markup=categories_kb(price["categories"], len(cart)),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("item:") & ~F.data.startswith("item:back:"))
async def show_item(call: CallbackQuery, db: Database, state: FSMContext):
    item_id = call.data.split(":", 1)[1]
    item = db.get_item(item_id)
    if not item:
        await call.answer("Товар не найден.", show_alert=True)
        return

    data = await state.get_data()
    cart = get_cart(data)
    in_cart = item_id in get_cart_ids(cart)

    text = format_item_info(item)
    await call.message.edit_text(
        text,
        reply_markup=item_detail_kb(item_id, in_cart),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("item:back:"))
async def item_back(call: CallbackQuery, db: Database, state: FSMContext):
    item_id = call.data.split(":")[2]
    item = db.get_item(item_id)
    if not item:
        await price_back(call, db, state)
        return

    # Найти категорию товара
    price = db.get_price()
    cat = None
    for c in price["categories"]:
        for it in c["items"]:
            if it["id"] == item_id:
                cat = c
                break

    data = await state.get_data()
    cart = get_cart(data)
    cart_ids = get_cart_ids(cart)

    if cat:
        await call.message.edit_text(
            f"📁 <b>{cat['name']}</b>\n\nВыбери товар 👇",
            reply_markup=items_kb(cat["items"], cat["id"], cart_ids),
            parse_mode="HTML"
        )
    await call.answer()


@router.callback_query(F.data.startswith("cart:add:"))
async def add_to_cart(call: CallbackQuery, db: Database, state: FSMContext):
    item_id = call.data.split(":")[2]
    item = db.get_item(item_id)
    if not item:
        await call.answer("Товар не найден.", show_alert=True)
        return

    await state.update_data(pending_item_id=item_id)

    # Запрашиваем кол-во
    await call.message.answer(
        f"✏️ Укажи количество для <b>{item['name']}</b>\n"
        f"min - {item['min_qty']} ; 1.ед = {item['price']}₽ ; только {item.get('payment_types','1,2,3')}\n\n"
        f"Введи число (минимум {item['min_qty']}):",
        parse_mode="HTML"
    )
    await state.set_state(CartState.choosing_qty)
    await call.answer()


@router.message(CartState.choosing_qty)
async def process_qty(message: Message, db: Database, state: FSMContext):
    data = await state.get_data()
    item_id = data.get("pending_item_id")
    item = db.get_item(item_id)

    if not item:
        await message.answer("Ошибка. Начни сначала.")
        await state.clear()
        return

    text = message.text.strip()
    if not text.isdigit() or int(text) < item["min_qty"]:
        await message.answer(
            f"❌ Введи число не меньше {item['min_qty']}. Попробуй ещё раз:"
        )
        return

    qty = int(text)
    await state.update_data(pending_qty=qty)

    if item.get("has_target") and item.get("target_hint"):
        await message.answer(f"🎯 {item['target_hint']}")
        await state.set_state(CartState.choosing_target)
    else:
        await _add_item_to_cart(message, db, state, item, qty, target="")


@router.message(CartState.choosing_target)
async def process_target(message: Message, db: Database, state: FSMContext):
    data = await state.get_data()
    item_id = data.get("pending_item_id")
    qty = data.get("pending_qty", 1)
    item = db.get_item(item_id)
    target = message.text.strip()
    await _add_item_to_cart(message, db, state, item, qty, target=target)


async def _add_item_to_cart(message: Message, db: Database, state: FSMContext,
                             item: dict, qty: int, target: str):
    data = await state.get_data()
    cart = get_cart(data)

    # Если уже есть — обновляем
    existing = next((i for i in cart if i["id"] == item["id"]), None)
    if existing:
        existing["qty"] = qty
        existing["target"] = target
    else:
        cart.append({
            "id": item["id"],
            "name": item["name"],
            "price": item["price"],
            "qty": qty,
            "target": target,
        })

    await state.update_data(cart=cart, pending_item_id=None, pending_qty=None)
    await state.set_state(None)

    total = sum(i["price"] * i["qty"] for i in cart)
    await message.answer(
        f"✅ <b>{item['name']}</b> × {qty} добавлен в корзину!\n"
        f"🛒 В корзине: {len(cart)} позиций на {total}₽\n\n"
        f"Продолжай выбирать или оформи заказ 👇",
        reply_markup=_continue_kb(),
        parse_mode="HTML"
    )


def _continue_kb():
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🛒 Корзина", callback_data="cart:view"))
    kb.row(InlineKeyboardButton(text="◀️ Продолжить выбор", callback_data="menu:price"))
    kb.row(InlineKeyboardButton(text="🚫 Отменить 🚫", callback_data="cart:cancel"))
    return kb.as_markup()


@router.callback_query(F.data.startswith("cart:remove:"))
async def remove_from_cart(call: CallbackQuery, db: Database, state: FSMContext):
    item_id = call.data.split(":")[2]
    data = await state.get_data()
    cart = [i for i in get_cart(data) if i["id"] != item_id]
    await state.update_data(cart=cart)

    item = db.get_item(item_id)
    in_cart = False
    await call.message.edit_reply_markup(reply_markup=item_detail_kb(item_id, in_cart))
    await call.answer("Убрано из корзины.")