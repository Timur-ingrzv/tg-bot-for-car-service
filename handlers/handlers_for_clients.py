from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database.methods import db
from keyboards.keyboards_for_clients import get_interface_change_profile
from utils.states import ChangeClientProfile, UserStatus

router = Router()


@router.callback_query(F.data == "change client profile data")
async def change_profile_data(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберете поле, которое хотите изменить",
        reply_markup=get_interface_change_profile(),
    )


@router.callback_query(F.data.startswith("change-client-profile_"))
async def input_new_value(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(
        changed_field=callback.data.split("_", maxsplit=1)[1]
    )
    await state.set_state(ChangeClientProfile.waiting_for_new_value)
    await callback.message.answer("Введите новое значение")


@router.message(StateFilter(ChangeClientProfile.waiting_for_new_value))
async def change_client_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(UserStatus.client)
    changed_field = data["changed_field"]
    new_value = message.text.strip()
    if new_value == "":
        await message.answer("Новое значение не может быть пустой строкой")
        return

    if changed_field == "phone_number" and len(new_value) != 11:
        await message.answer("Новый номер телефона должен содержать 11 цифр")
        return

    result = await db.change_profile(data["user_id"], changed_field, new_value)
    await message.answer(result)
