"""Telegram user conversion."""

from aiogram.types import User

from app.services.conversation import Identity


def identity_of(user: User) -> Identity:
    return Identity(user.id, user.username, user.first_name)
