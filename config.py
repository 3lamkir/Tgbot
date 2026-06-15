"""
config.py — Конфигурация бота.

Настройка через консоль (интерактивно при первом запуске):
  /addapibot   — добавить токен бота
  /adduser     — добавить ID администратора

Или просто впиши значения прямо здесь в переменные ниже.
"""

import json
import os
import sys

CONFIG_FILE = "data/config.json"

# ─── Значения по умолчанию (можно вписать сюда вручную) ──────────────────────
_defaults = {
    "BOT_TOKEN": "",          # токен от @BotFather
    "ADMIN_IDS": [],          # список ID администраторов
    "GROUP_ID": None,         # ID супергруппы для заказов (привязывается командой)
    "SUPPORT_LINK": "@username",  # ссылка/юзернейм поддержки
}
# ─────────────────────────────────────────────────────────────────────────────


def _load() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # дополняем новыми ключами если появились
        for k, v in _defaults.items():
            data.setdefault(k, v)
        return data
    return dict(_defaults)


def _save(cfg: dict):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _console_setup():
    """Интерактивная настройка через консольные команды."""
    print("\n╔══════════════════════════════════════╗")
    print("║        НАСТРОЙКА БОТА               ║")
    print("╚══════════════════════════════════════╝")
    print("Команды:")
    print("  /addapibot   — задать токен бота")
    print("  /adduser     — добавить ID администратора")
    print("  /start       — запустить бота (если всё задано)")
    print("  /status      — показать текущие настройки")
    print("  /exit        — выйти\n")

    cfg = _load()

    while True:
        cmd = input(">> ").strip()

        if cmd == "/addapibot":
            token = input("Введи токен бота: ").strip()
            cfg["BOT_TOKEN"] = token
            _save(cfg)
            print("✅ Токен сохранён.")

        elif cmd == "/adduser":
            uid = input("Введи Telegram ID администратора: ").strip()
            if uid.lstrip("-").isdigit():
                if int(uid) not in cfg["ADMIN_IDS"]:
                    cfg["ADMIN_IDS"].append(int(uid))
                    _save(cfg)
                    print(f"✅ Администратор {uid} добавлен.")
                else:
                    print("⚠️ Этот ID уже есть в списке.")
            else:
                print("❌ Неверный формат ID.")

        elif cmd == "/status":
            print(f"\n📋 Текущие настройки:")
            print(f"  Токен: {'задан ✅' if cfg['BOT_TOKEN'] else 'НЕ задан ❌'}")
            print(f"  Администраторы: {cfg['ADMIN_IDS'] or 'нет'}")
            print(f"  Группа: {cfg['GROUP_ID'] or 'не привязана'}")
            print(f"  Поддержка: {cfg['SUPPORT_LINK']}\n")

        elif cmd == "/start":
            if not cfg["BOT_TOKEN"]:
                print("❌ Сначала задай токен (/addapibot).")
            elif not cfg["ADMIN_IDS"]:
                print("❌ Добавь хотя бы одного администратора (/adduser).")
            else:
                print("🚀 Запускаю бота...")
                return cfg

        elif cmd == "/exit":
            sys.exit(0)

        else:
            print("Неизвестная команда. Используй /addapibot, /adduser, /start, /status, /exit")


# ─── Загрузка конфига ─────────────────────────────────────────────────────────
_cfg = _load()

# Если токен не задан — запускаем интерактивную настройку
if not _cfg["BOT_TOKEN"] or not _cfg["ADMIN_IDS"]:
    _cfg = _console_setup()
    _save(_cfg)

BOT_TOKEN: str = _cfg["BOT_TOKEN"]
ADMIN_IDS: list[int] = _cfg["ADMIN_IDS"]
GROUP_ID: int | None = _cfg.get("GROUP_ID")
SUPPORT_LINK: str = _cfg.get("SUPPORT_LINK", "@username")


def reload_config():
    """Перечитать конфиг с диска (используется после изменений в боте)."""
    global BOT_TOKEN, ADMIN_IDS, GROUP_ID, SUPPORT_LINK
    c = _load()
    BOT_TOKEN = c["BOT_TOKEN"]
    ADMIN_IDS = c["ADMIN_IDS"]
    GROUP_ID = c.get("GROUP_ID")
    SUPPORT_LINK = c.get("SUPPORT_LINK", "@username")
    return c


def save_config(**kwargs):
    """Сохранить изменения в конфиг."""
    c = _load()
    c.update(kwargs)
    _save(c)
    reload_config()