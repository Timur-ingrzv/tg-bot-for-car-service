from aiogram import F, Router
from aiogram.types import Message

router = Router()

@router.message(F.text == "test_un")
async def test1(message: Message):
    await message.answer("выполнено для неавторизированного")