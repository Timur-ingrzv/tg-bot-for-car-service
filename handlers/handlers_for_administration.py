from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message()
async def unknown_message(message: types.Message):
    await message.answer("Я не понимаю, напишите /help или используйте кнопки")
