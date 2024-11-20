from aiogram import F, Router, types
from aiogram.types import Message
from aiogram.utils.formatting import (
    Bold, as_list, as_marked_section, as_key_value, HashTag
)

from config import AVAILABLE_SERVICES

router = Router()

@router.callback_query(F.data == "services")
async def print_services(callback: types.CallbackQuery):
    new_list = '\n'.join([f"{i + 1}. {AVAILABLE_SERVICES[i]}" for i in range(len(AVAILABLE_SERVICES))])
    content = as_marked_section(
        Bold("Доступные услуги:"),
        new_list,
        marker=""
    )
    await callback.message.answer(**content.as_kwargs())

@router.callback_query(F.data == "authorization")
async def authorization(callback: types.CallbackQuery):
    pass

@router.callback_query(F.data == "registration")
async def registration(callback: types.CallbackQuery):
    pass