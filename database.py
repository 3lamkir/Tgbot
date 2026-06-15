"""
database.py — Хранилище данных (JSON-файлы).
Все данные сохраняются и не сбрасываются при перезапуске бота.
"""

import json
import os
from datetime import datetime
from typing import Optional

DATA_DIR = "data"

USERS_FILE = f"{DATA_DIR}/users.json"
ORDERS_FILE = f"{DATA_DIR}/orders.json"
PRICE_FILE = f"{DATA_DIR}/price.json"
SETTINGS_FILE = f"{DATA_DIR}/settings.json"
TOPICS_FILE = f"{DATA_DIR}/topics.json"  # user_id -> topic_id в супергруппе


class Database:
    def init(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        # Создаём файлы если нет
        for fpath, default in [
            (USERS_FILE, {}),
            (ORDERS_FILE, {}),
            (TOPICS_FILE, {}),
            (SETTINGS_FILE, {
                "welcome_text": (
                    "👋 Привет, {name}!\n\n"
                    "Добро пожаловать! Выбери нужный раздел ниже 👇"
                ),
                "price_text": (
                    "📋 <b>Прайс-лист</b>\n\n"
                    "Выбери категорию товаров 👇"
                ),
                "support_link": "@username",
            }),
            (PRICE_FILE, {
                "categories": [
                    {
                        "id": "tg",
                        "name": "📱 Тг",
                        "items": [
                            {
                                "id": "tg_stars",
                                "name": "⭐ Тг звёзды",
                                "price": 1,
                                "min_qty": 50,
                                "payment_types": "1,2,3",
                                "target_hint": "Укажите @user на котором хотите купить звёзды",
                                "has_target": True,
                            },
                            {
                                "id": "tg_text",
                                "name": "📝 Текст",
                                "price": 5,
                                "min_qty": 1,
                                "payment_types": "1,2,3",
                                "target_hint": "",
                                "has_target": False,
                            },
                        ],
                    },
                    {
                        "id": "bot",
                        "name": "🤖 Бот",
                        "items": [
                            {
                                "id": "bot_art",
                                "name": "🎨 Арт",
                                "price": 100,
                                "min_qty": 1,
                                "payment_types": "1,2,3",
                                "target_hint": "",
                                "has_target": False,
                            },
                            {
                                "id": "bot_ilo",
                                "name": "✏️ Ило",
                                "price": 200,
                                "min_qty": 1,
                                "payment_types": "1,2,3",
                                "target_hint": "",
                                "has_target": False,
                            },
                        ],
                    },
                ]
            }),
        ]:
            if not os.path.exists(fpath):
                self._write(fpath, default)

    # ─── Внутренние методы ─────────────────────────────────────────────────

    def _read(self, path: str) -> dict | list:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path: str, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ─── Пользователи ──────────────────────────────────────────────────────

    def get_user(self, user_id: int) -> Optional[dict]:
        users = self._read(USERS_FILE)
        return users.get(str(user_id))

    def upsert_user(self, user_id: int, first_name: str, username: str = ""):
        users = self._read(USERS_FILE)
        uid = str(user_id)
        if uid not in users:
            users[uid] = {
                "id": user_id,
                "first_name": first_name,
                "username": username,
                "started_at": datetime.now().isoformat(),
                "total_orders": 0,
                "total_spent_rub": 0,
            }
        else:
            users[uid]["first_name"] = first_name
            users[uid]["username"] = username
        self._write(USERS_FILE, users)

    def get_all_users(self) -> dict:
        return self._read(USERS_FILE)

    # ─── Заказы ────────────────────────────────────────────────────────────

    def create_order(self, user_id: int, cart: list, payment_type: int,
                     total_rub: float, total_display: str) -> str:
        orders = self._read(ORDERS_FILE)
        order_id = f"{user_id}_{int(datetime.now().timestamp())}"
        orders[order_id] = {
            "id": order_id,
            "user_id": user_id,
            "cart": cart,
            "payment_type": payment_type,
            "total_rub": total_rub,
            "total_display": total_display,
            "status": "active",   # active | done | cancelled
            "created_at": datetime.now().isoformat(),
            "topic_id": None,
        }
        self._write(ORDERS_FILE, orders)
        return order_id

    def get_order(self, order_id: str) -> Optional[dict]:
        orders = self._read(ORDERS_FILE)
        return orders.get(order_id)

    def update_order(self, order_id: str, **kwargs):
        orders = self._read(ORDERS_FILE)
        if order_id in orders:
            orders[order_id].update(kwargs)
            self._write(ORDERS_FILE, orders)

    def get_user_orders(self, user_id: int) -> list[dict]:
        orders = self._read(ORDERS_FILE)
        return [o for o in orders.values() if o["user_id"] == user_id]

    def get_all_orders(self) -> dict:
        return self._read(ORDERS_FILE)

    def finish_order(self, order_id: str):
        orders = self._read(ORDERS_FILE)
        if order_id not in orders:
            return
        orders[order_id]["status"] = "done"
        orders[order_id]["finished_at"] = datetime.now().isoformat()
        self._write(ORDERS_FILE, orders)

        # Обновляем статистику пользователя
        uid = orders[order_id]["user_id"]
        users = self._read(USERS_FILE)
        u = users.get(str(uid))
        if u:
            u["total_orders"] = u.get("total_orders", 0) + 1
            u["total_spent_rub"] = u.get("total_spent_rub", 0) + orders[order_id]["total_rub"]
            self._write(USERS_FILE, users)

    def cancel_order(self, order_id: str):
        orders = self._read(ORDERS_FILE)
        if order_id in orders:
            orders[order_id]["status"] = "cancelled"
            orders[order_id]["cancelled_at"] = datetime.now().isoformat()
            self._write(ORDERS_FILE, orders)

    # ─── Темы (топики) супергруппы ─────────────────────────────────────────

    def get_topic(self, user_id: int) -> Optional[int]:
        topics = self._read(TOPICS_FILE)
        t = topics.get(str(user_id))
        return t

    def set_topic(self, user_id: int, topic_id: int):
        topics = self._read(TOPICS_FILE)
        topics[str(user_id)] = topic_id
        self._write(TOPICS_FILE, topics)

    # ─── Настройки ─────────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None):
        s = self._read(SETTINGS_FILE)
        return s.get(key, default)

    def set_setting(self, key: str, value):
        s = self._read(SETTINGS_FILE)
        s[key] = value
        self._write(SETTINGS_FILE, s)

    # ─── Прайс ─────────────────────────────────────────────────────────────

    def get_price(self) -> dict:
        return self._read(PRICE_FILE)

    def save_price(self, price_data: dict):
        self._write(PRICE_FILE, price_data)

    def get_category(self, cat_id: str) -> Optional[dict]:
        price = self.get_price()
        for cat in price["categories"]:
            if cat["id"] == cat_id:
                return cat
        return None

    def get_item(self, item_id: str) -> Optional[dict]:
        price = self.get_price()
        for cat in price["categories"]:
            for item in cat["items"]:
                if item["id"] == item_id:
                    return item
        return None

    def add_category(self, cat_id: str, name: str):
        price = self.get_price()
        price["categories"].append({"id": cat_id, "name": name, "items": []})
        self.save_price(price)

    def add_item(self, cat_id: str, item: dict):
        price = self.get_price()
        for cat in price["categories"]:
            if cat["id"] == cat_id:
                cat["items"].append(item)
                break
        self.save_price(price)

    def update_item(self, item_id: str, **kwargs):
        price = self.get_price()
        for cat in price["categories"]:
            for item in cat["items"]:
                if item["id"] == item_id:
                    item.update(kwargs)
        self.save_price(price)

    def delete_item(self, item_id: str):
        price = self.get_price()
        for cat in price["categories"]:
            cat["items"] = [i for i in cat["items"] if i["id"] != item_id]
        self.save_price(price)

    def delete_category(self, cat_id: str):
        price = self.get_price()
        price["categories"] = [c for c in price["categories"] if c["id"] != cat_id]
        self.save_price(price)

    # ─── Активный заказ пользователя (последний active) ────────────────────

    def get_active_order(self, user_id: int) -> Optional[dict]:
        orders = self._read(ORDERS_FILE)
        user_orders = [
            o for o in orders.values()
            if o["user_id"] == user_id and o["status"] == "active"
        ]
        if not user_orders:
            return None
        return sorted(user_orders, key=lambda x: x["created_at"])[-1]