"""
utils/helpers.py — Вспомогательные функции.
"""

from datetime import datetime


PAYMENT_NAMES = {
    1: "Рубли (₽)",
    2: "Звёзды Тг (⭐)",
    3: "Другая валюта 💳",
}

PAYMENT_COMMISSION = {
    1: 0.0,    # без комиссии
    2: 0.15,   # +15%
    3: 0.10,   # +10%
}

PAYMENT_SYMBOLS = {
    1: "₽",
    2: "⭐",
    3: "💳",
}


def calc_total(cart: list, payment_type: int) -> tuple[float, float, str]:
    """
    Возвращает (total_rub, total_with_commission, display_str).
    """
    total_rub = sum(item["price"] * item["qty"] for item in cart)
    commission = PAYMENT_COMMISSION[payment_type]
    total_final = total_rub * (1 + commission)
    symbol = PAYMENT_SYMBOLS[payment_type]

    if payment_type == 1:
        display = f"{total_final:.0f}₽"
    else:
        display = f"{total_final:.0f}{symbol} (~{total_rub:.0f}₽)"

    return total_rub, total_final, display


def format_cart_text(cart: list, payment_type: int | None = None) -> str:
    if not cart:
        return "Корзина пуста."

    lines = ["🛒 <b>Корзина:</b>\n"]
    total = 0
    for item in cart:
        subtotal = item["price"] * item["qty"]
        total += subtotal
        target_line = f"\n   └ 🎯 {item['target']}" if item.get("target") else ""
        lines.append(
            f"• {item['name']} × {item['qty']} ед. = {subtotal}₽{target_line}"
        )

    lines.append(f"\n💰 Итого (без комиссии): <b>{total}₽</b>")

    if payment_type:
        _, final, display = calc_total(cart, payment_type)
        comm = PAYMENT_COMMISSION[payment_type]
        if comm > 0:
            lines.append(f"📊 Комиссия {int(comm*100)}%: +{final - total:.0f}₽")
        lines.append(f"💳 К оплате: <b>{display}</b>")

    return "\n".join(lines)


def format_order_message(user, cart: list, payment_type: int, total_rub: float, total_display: str) -> str:
    name = user.get("first_name", "Неизвестно")
    username = f"@{user['username']}" if user.get("username") else f"ID: {user['id']}"

    lines = [
        f"🆕 <b>Новый заказ</b> от <b>{name}</b> ({username})\n",
        "📦 <b>Товары:</b>",
    ]
    for item in cart:
        subtotal = item["price"] * item["qty"]
        lines.append(f"• {item['name']} × {item['qty']} ед. = {subtotal}₽")
        if item.get("target"):
            lines.append(f"   └ 🎯 {item['target']}")

    lines.append(f"\n💳 <b>Способ оплаты:</b> {PAYMENT_NAMES[payment_type]}")

    comm = PAYMENT_COMMISSION[payment_type]
    if comm > 0:
        lines.append(f"📊 Комиссия: {int(comm*100)}%")

    lines.append(f"\n💰 <b>Вся сумма заказа:</b> {total_display} (= {total_rub:.0f}₽)")

    return "\n".join(lines)


def format_receipts(user: dict, orders: list) -> str:
    total_count = len(orders)
    total_spent = sum(o.get("total_rub", 0) for o in orders if o["status"] == "done")

    lines = [
        "🧾 <b>Ваши заказы</b>\n",
        f"📦 Всего заказов: <b>{total_count}</b>",
        f"💸 Потрачено: <b>{total_spent:.0f}₽</b>\n",
        "📋 <b>Что вы заказывали:</b>",
    ]

    if not orders:
        lines.append("— пока ничего нет")
    else:
        for o in sorted(orders, key=lambda x: x["created_at"], reverse=True):
            dt = datetime.fromisoformat(o["created_at"]).strftime("%d.%m.%Y %H:%M")
            status_emoji = {"active": "⏳", "done": "✅", "cancelled": "❌"}.get(o["status"], "❓")
            lines.append(f"\n{status_emoji} <b>{dt}</b>")
            for item in o["cart"]:
                subtotal = item["price"] * item["qty"]
                lines.append(f"  • {item['name']} × {item['qty']} = {subtotal}₽")
            lines.append(f"  💳 Итого: <b>{o['total_display']}</b>")

    return "\n".join(lines)


def format_item_info(item: dict) -> str:
    pay_map = {"1": "₽", "2": "⭐", "3": "💳"}
    pay_types = ", ".join(pay_map.get(p.strip(), p) for p in item.get("payment_types", "1,2,3").split(","))

    lines = [
        f"<b>{item['name']}</b>\n",
        f"💰 Цена: <b>{item['price']}₽</b> за 1 ед.",
        f"📦 Минимум: <b>{item['min_qty']}</b> ед.",
        f"💳 Оплата: {pay_types}",
    ]
    if item.get("has_target") and item.get("target_hint"):
        lines.append(f"\n🎯 {item['target_hint']}")

    lines.append("\n✏️ — указать кол-во")
    lines.append(f"min - {item['min_qty']} ; 1.ед = {item['price']}₽ ; только {item.get('payment_types','1,2,3')}")

    return "\n".join(lines)