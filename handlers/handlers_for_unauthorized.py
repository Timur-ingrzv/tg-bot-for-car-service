from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from keyboards import keyboards_for_unauthorized
from keyboards.keyboards_for_administration import get_interface_for_admin
from keyboards.keyboards_for_clients import get_interface_for_client
from keyboards.keyboards_for_unauthorized import get_start_keyboard
from utils.middlewares import MessageLengthMiddleware, SQLInjectionMiddleware
from utils.states import Authorization, UserStatus, Registration
from database.methods import db

router = Router()
router.message.middleware.register(MessageLengthMiddleware())
router.message.middleware(SQLInjectionMiddleware())


@router.callback_query(F.data == "list services")
async def print_services(callback: types.CallbackQuery):
    res = await db.show_services()
    if isinstance(res, str):
        await callback.message.answer(res)
        return

    all_services = ""
    for service in res:
        all_services += (
            f"• {service['service_name']} - {service['price']} руб.\n"
        )
    await callback.message.answer(all_services)


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
        await state.update_data(status=user["status"])
        await db.change_chat_id(user["id"], message.chat.id)
        # выбираем интерфейс от статуса
        if user["status"] == "client":
            await state.set_state(UserStatus.client)
            interface = get_interface_for_client()
        else:
            await state.set_state(UserStatus.admin)
            interface = get_interface_for_admin()
        await message.answer(
            f"С возвращением, {user['name']}", reply_markup=interface
        )


@router.callback_query(F.data == "registration")
async def input_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Registration.waiting_for_name)
    await callback.message.answer("Введите имя")


@router.message(StateFilter(Registration.waiting_for_name))
async def input_login(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if await db.check_existing(name=name):
        await message.answer("Данное имя занято, попробуйте другое")
        return

    await state.update_data(name=name)
    await state.set_state(Registration.waiting_for_login)
    await message.answer("Введите логин")


@router.message(StateFilter(Registration.waiting_for_login))
async def input_password(message: types.Message, state: FSMContext):
    login = message.text.strip()
    if await db.check_existing(login=login):
        await message.answer("Данный логин занят, попробуйте другой")
        return
    await state.update_data(login=message.text.strip())
    await state.set_state(Registration.waiting_for_password)
    await message.answer("Введите пароль")


@router.message(StateFilter(Registration.waiting_for_password))
async def input_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await state.set_state(Registration.waiting_for_phone_number)
    await message.answer("Введите номер телефона(только цифры или +")


@router.message(StateFilter(Registration.waiting_for_phone_number))
async def registration(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()
    if not all(sym in "123456789+ ()" for sym in phone_number):
        await message.answer(
            "Введите корректный номер телефона(пример: +79998593535)"
        )
        return
    data = await state.get_data()
    data["phone_number"] = phone_number
    data["status"] = "client"
    data["chat_id"] = message.chat.id
    res = await db.add_user(data)
    await state.clear()
    await message.answer(res)
