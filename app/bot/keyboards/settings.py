"""Style selection keyboard."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

STYLE_LABELS = {"short": "Кратко", "normal": "Обычно", "detailed": "Подробно"}


def style_keyboard(current: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=("✓ " if current == style else "") + label,
            callback_data=f"style:{style}",
        )]
        for style, label in STYLE_LABELS.items()
    ])
