"""
handlers/support.py — Поддержка.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database import Database

router = Router()


@router.callback_query(F.data == "menu:support")
async def show_support(call: CallbackQuery, db: Database):
    support_link = db.get_setting("support_link", "@username")
    import config
    support_link = config.SUPPORT_LINK  # берём из конфига

    kb = InlineKeyboardBuilder()
    if support_link.startswith("@"):
        url = f"https://t.me/{support_link.lstrip('@')}"
        kb.row(InlineKeyboardButton(text="💬 Написать в поддержку", url=url))
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:back"))

    await call.message.edit_text(
        f"🆘 <b>Поддержка</b>\n\n"
        f"По всем вопросам обращайся: {support_link}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await call.answer()