"""
handlers/start.py — /start и главное меню.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database import Database
from utils.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    db.upsert_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username or "",
    )

    welcome = db.get_setting("welcome_text",
        "👋 Привет, {name}!\n\nДобро пожаловать! Выбери нужный раздел ниже 👇")
    text = welcome.replace("{name}", message.from_user.first_name)

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu:back")
async def back_to_menu(call: CallbackQuery, db: Database):
    welcome = db.get_setting("welcome_text",
        "👋 Привет, {name}!\n\nДобро пожаловать! Выбери нужный раздел ниже 👇")
    text = welcome.replace("{name}", call.from_user.first_name)

    await call.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await call.answer()