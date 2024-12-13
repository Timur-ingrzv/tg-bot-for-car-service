from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.formatting import Bold, as_marked_section

from config import AVAILABLE_SERVICES
from keyboards import keyboards_for_unauthorized
from keyboards.keyboards_for_clients import get_interface_for_client
from keyboards.keyboards_for_unauthorized import get_start_keyboard
from utils.middlewares import MessageLengthMiddleware
from utils.states import Authorization, UserStatus, Registration
from database.methods import db

router = Router()
router.message.middleware.register(MessageLengthMiddleware())


@router.callback_query(F.data == "services")
async def print_services(callback: types.CallbackQuery):
    new_list = "\n".join(
        [
            f"{i + 1}. {AVAILABLE_SERVICES[i]}"
            for i in range(len(AVAILABLE_SERVICES))
        ]
    )
    content = as_marked_section(Bold("Доступные услуги:"), new_list, marker="")
    await callback.message.answer(**content.as_kwargs())


@router.callback_query(F.data == "authorization")
async def enter_login(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите логин")
    await state.set_state(Authorization.waiting_for_login)


@router.message(StateFilter(Authorization.waiting_for_login))
async def enter_password(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Введите пароль")
    await state.set_state(Authorization.waiting_for_password)


@router.message(StateFilter(Authorization.waiting_for_password))
async def authorization(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user = await db.find_user(user_data["login"], message.text)
    await state.clear()
    if not user:
        await message.answer(
            "Неверный логин или пароль\n"
            "Попробуйте еще раз или зарегистрируйтесь",
            reply_markup=keyboards_for_unauthorized.get_start_keyboard(),
        )
        return

    if "Ошибка" in user["status"]:
        await message.answer(user["status"])
    else:
        await state.update_data(user_id=user["id"])
        # выбираем интерфейс от статуса
        if user["status"] == "client":
            await state.set_state(UserStatus.client)
            interface = get_interface_for_client()
        else:
            await state.set_state(UserStatus.admin)
            interface = None

        await message.answer(
            f"С возвращением, {user['name']}", reply_markup=interface
        )


@router.callback_query(F.data == "registration")
async def input_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Registration.waiting_for_name)
    await callback.message.answer("Введите имя")


@router.message(StateFilter(Registration.waiting_for_name))
async def input_login(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Registration.waiting_for_login)
    await message.answer("Введите логин")


@router.message(StateFilter(Registration.waiting_for_login))
async def input_password(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(Registration.waiting_for_password)
    await message.answer("Введите пароль")


@router.message(StateFilter(Registration.waiting_for_password))
async def input_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await state.set_state(Registration.waiting_for_phone_number)
    await message.answer("Введите номер телефона(только цифры начиная с 8)")


@router.message(StateFilter(Registration.waiting_for_phone_number))
async def registration(message: types.Message, state: FSMContext):
    phone_number = message.text
    if len(phone_number.strip()) != 11:
        await state.clear()
        await message.answer(
            "Неправильный номер телефона, должно быть 11 символов",
            reply_markup=get_start_keyboard(),
        )
        return

    data = await state.get_data()
    data["phone_number"] = phone_number
    data["status"] = "client"
    data["chat_id"] = message.chat.id
    res = await db.add_user(data)
    await state.clear()
    await message.answer(res)
