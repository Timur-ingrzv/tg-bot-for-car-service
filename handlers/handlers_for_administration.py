from datetime import datetime, timedelta, time

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext

from aiogram_calendar import SimpleCalendarCallback
import logging

from database.methods import db
from keyboards.keyboards_for_administration import (
    get_day_week,
    generate_page_buttons,
    get_interface_manage_users,
    get_interface_manage_workers,
    get_interface_manage_schedule,
    get_interface_for_admin,
    get_status,
)
from keyboards.keyboards_for_clients import get_services_to_add_schedule
from utils.calendar import get_calendar
from utils.middlewares import SQLInjectionMiddleware
from utils.states import (
    SchedulerAdmin,
    UserStatus,
    WorkingTime,
    Statistic,
    UsersAdmin,
)

router = Router()
router.message.middleware(SQLInjectionMiddleware())


@router.callback_query(F.data == "clients")
async def show_managment_of_clients(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление клиентами", reply_markup=get_interface_manage_users()
    )


@router.callback_query(F.data == "workers")
async def show_managment_of_clients(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление сотрудниками", reply_markup=get_interface_manage_workers()
    )


@router.callback_query(F.data == "schedule")
async def show_managment_of_clients(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление расписанием", reply_markup=get_interface_manage_schedule()
    )


@router.callback_query(F.data == "back admin")
async def go_back_admin(callback: types.CallbackQuery):
    await callback.message.answer(
        "Доступные опции для администратора:",
        reply_markup=get_interface_for_admin(),
    )


@router.callback_query(F.data == "add record")
async def input_client_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_client_name_to_add)
    await callback.message.answer("Введите имя клиента")


@router.message(StateFilter(SchedulerAdmin.waiting_for_client_name_to_add))
async def input_worker_name(message: types.Message, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_worker_name_to_add)
    await state.update_data(client_name=message.text.strip())
    await message.answer("Введите имя работника")


@router.message(StateFilter(SchedulerAdmin.waiting_for_worker_name_to_add))
async def input_service_name(message: types.Message, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_service_to_add)
    await state.update_data(worker_name=message.text.strip())
    await message.answer(
        "Выберите услугу:", reply_markup=await get_services_to_add_schedule()
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_service_to_add),
    F.data.startswith("choose-service_"),
)
async def input_date_to_add(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SchedulerAdmin.waiting_for_date_to_add)
    service_name = callback.data.split("_", maxsplit=1)[1]
    await state.update_data(service_name=service_name)
    calendar, cur_time = await get_calendar(callback.from_user)

    from bot import bot

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"Вы выбрали услугу <b>{service_name}</b>",
        reply_markup=None,
        parse_mode="HTML",
    )

    await callback.message.answer(
        "Выберите дату для удаления записи",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_date_to_add),
    SimpleCalendarCallback.filter(),
)
async def input_time_to_add(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar, cur_time = await get_calendar(callback.from_user)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerAdmin.waiting_for_time_to_add)
        await state.update_data(date=date)
        await callback.message.answer(
            "Введите время записи для добавления - час дня"
        )


@router.message(StateFilter(SchedulerAdmin.waiting_for_time_to_add))
async def add_scheduler(message: types.Message, state: FSMContext):
    await state.set_state(UserStatus.admin)
    try:
        valid_time = int(message.text.strip())
        if not (0 <= valid_time < 24):
            await message.answer("Время должно быть в диапазоне от 0 до 23")
            return

        data = await state.get_data()
        await state.clear()
        await state.set_state(UserStatus.admin)
        await state.update_data(user_id=data["user_id"])
        await state.update_data(status=data["status"])

        valid_date = datetime.combine(data["date"], time(hour=valid_time))
        info = {
            "date": valid_date,
            "client_name": data["client_name"],
            "worker_name": data["worker_name"],
            "service_name": data["service_name"],
        }
        res = await db.add_schedule_admin(info)
        await message.answer(res)

    except Exception as e:
        await message.answer(
            "Неправильный формат времени - введите число от 0 до 23"
        )


@router.callback_query(F.data == "delete record")
async def input_name_to_delete(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerAdmin.waiting_for_name_to_delete)
    await callback.message.answer("Введите имя клиента или работника")


@router.message(StateFilter(SchedulerAdmin.waiting_for_name_to_delete))
async def input_date_to_delete(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(SchedulerAdmin.waiting_for_date_to_delete)
    calendar, cur_time = await get_calendar(message.from_user)
    await message.answer(
        "Выберите дату для удаления записи",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_date_to_delete),
    SimpleCalendarCallback.filter(),
)
async def input_time_to_delete(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar, cur_time = await get_calendar(callback.from_user)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerAdmin.waiting_for_time_to_delete)
        await state.update_data(date=date)
        await callback.message.answer(
            "Введите время записи для удаления - час дня"
        )


@router.message(StateFilter(SchedulerAdmin.waiting_for_time_to_delete))
async def delete_scheduler(message: types.Message, state: FSMContext):
    await state.set_state(UserStatus.admin)
    try:
        valid_time = int(message.text.strip())
        if not (0 <= valid_time < 24):
            await state.set_state(UserStatus.client)
            await message.answer(
                "Время должно быть целое число в диапазоне от 0 до 23"
            )
            return

        data = await state.get_data()
        await state.clear()
        await state.set_state(UserStatus.admin)
        await state.update_data(user_id=data["user_id"])
        await state.update_data(status=data["status"])

        valid_date = datetime.combine(data["date"], time(hour=valid_time))
        name = data["name"]
        res = await db.delete_schedule(name, valid_date)
        await message.answer(res)

    except Exception:
        await message.answer(
            "Неправильный формат времени - введите число от 0 до 23"
        )


@router.callback_query(F.data == "show records for admin")
async def input_start_date_to_show(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(SchedulerAdmin.waiting_for_start_to_show)
    calendar, cur_time = await get_calendar(callback.from_user)
    await callback.message.answer(
        "Выберите дату начала диапазона для просмотра",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_start_to_show),
    SimpleCalendarCallback.filter(),
)
async def input_end_date_to_show(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar, cur_time = await get_calendar(callback.from_user)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.set_state(SchedulerAdmin.waiting_for_end_to_show)
        await state.update_data(start=date)

        calendar, cur_time = await get_calendar(callback.from_user)
        await callback.message.answer(
            "Выберите дату конца диапазона для просмотра",
            reply_markup=await calendar.start_calendar(
                year=cur_time.year, month=cur_time.month
            ),
        )


@router.callback_query(
    StateFilter(SchedulerAdmin.waiting_for_end_to_show),
    SimpleCalendarCallback.filter(),
)
async def show_schedule_for_admin(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar, cur_time = await get_calendar(callback.from_user)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        user_data = await state.get_data()
        await state.clear()
        await state.update_data(user_id=user_data["user_id"])
        await state.update_data(status=user_data["status"])
        await state.set_state(UserStatus.admin)

        start = user_data["start"]
        end = date + timedelta(days=1)
        if start > end:
            await callback.message.answer(
                "Начало диапазона должно быть раньше конца"
            )
            return
        schedule = await db.show_schedule_admin(start, end)
        if not schedule:
            await callback.message.answer("В данный период нет записей")
            return

        for note in schedule:
            await callback.message.answer(
                f"<b>Название услуги:</b> {note['service_name']}\n"
                f"<b>Клиент:</b> {note['client_name']}\n"
                f"<b>Работник:</b> {note['worker_name']}\n"
                f"<b>Цена:</b> {note['price']}\n"
                f"<b>Дата:</b> {note['date'].strftime('%d-%m-%Y %H-%M')}\n",
                parse_mode="HTML",
            )


@router.callback_query(F.data == "change working time")
async def input_worker_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WorkingTime.waiting_worker_name)
    await callback.message.answer("Введите имя работника")


@router.message(StateFilter(WorkingTime.waiting_worker_name))
async def input_weekday(message: types.Message, state: FSMContext):
    worker_name = message.text.strip()
    worker_id = await db.find_worker(worker_name)
    if not worker_id:
        await state.set_state(UserStatus.admin)
        await message.answer("Работника с таким именем не существует")
        return

    await state.set_state(WorkingTime.waiting_weekday)
    await state.update_data(worker_id=worker_id)
    await message.answer("Выберите день недели", reply_markup=get_day_week())


@router.callback_query(
    StateFilter(WorkingTime.waiting_weekday), F.data.startswith("day_")
)
async def input_time(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WorkingTime.waiting_time)
    weekday = int(callback.data.split("_")[1])
    await state.update_data(weekday=weekday)
    await callback.message.answer(
        "Введите время начала и конца рабочего времени"
        " в формате hours-hours(Если в этот день сотрудник"
        " не работает, то введите 0)"
    )


@router.message(StateFilter(WorkingTime.waiting_time))
async def change_working_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await state.update_data(user_id=data["user_id"])
    await state.update_data(status=data["status"])
    await state.set_state(UserStatus.admin)

    working_time = message.text.strip()
    if working_time == "0":
        res = await db.delete_working_time(
            int(data["worker_id"]), int(data["weekday"])
        )
        await message.answer(res)
        return

    try:
        start, end = map(int, working_time.split("-"))
        start = time(hour=start)
        end = time(hour=end)
        res = await db.add_working_time(
            int(data["worker_id"]), start, end, int(data["weekday"])
        )
        await message.answer(res)

    except Exception as e:
        logging.error(e)
        await message.answer("Неправильный формат времени")


@router.callback_query(F.data == "show working time for worker")
async def input_worker_name(callback: types.callback_query, state: FSMContext):
    await state.set_state(WorkingTime.waiting_worker_name_to_show)
    await callback.message.answer("Введите имя работника")


@router.message(StateFilter(WorkingTime.waiting_worker_name_to_show))
async def show_working_time(message: types.Message, state: FSMContext):
    await state.set_state(UserStatus.admin)
    worker_name = message.text.strip()
    res = await db.show_working_time(worker_name)
    if isinstance(res, str):
        await message.answer(res)
        return

    ans = f"<b>{worker_name}</b>\n"
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    working_time = ["Не работает"] * 7
    for day in res:
        working_time[day["day_week"]] = (
            f"{day['time_start'].strftime('%H:%M')} - "
            f"{day['time_end'].strftime('%H:%M')}"
        )

    for idx in range(7):
        ans += f"<b>{days[idx]}:</b> {working_time[idx]}\n"

    await message.answer(ans, parse_mode="HTML")


@router.callback_query(F.data == "show workers info")
async def show_workers_info(callback: types.CallbackQuery, state: FSMContext):
    workers_groups = await db.show_workers_info()
    if isinstance(workers_groups, str):
        await callback.message.answer(workers_groups)
        return
    ans = ""
    for el in workers_groups["working_free"]:
        ans += f"<b>{el['name']}:</b> Рабочее время, свободен\n"
    for el in workers_groups["working_not_free"]:
        ans += (
            f"<b>{el['name']}:</b> Рабочее время, занят выполнением услуги\n"
        )
    for el in workers_groups["not_working"]:
        ans += f"<b>{el['name']}:</b> Не работает\n"
    await callback.message.answer(ans, parse_mode="HTML")


@router.callback_query(F.data == "statistic")
async def input_start_date(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Statistic.waiting_start_date)
    calendar, cur_time = await get_calendar(callback.from_user)
    await callback.message.answer(
        "Выберите дату начала промежутка",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(Statistic.waiting_start_date),
    SimpleCalendarCallback.filter(),
)
async def input_start_time(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar, cur_time = await get_calendar(callback.from_user)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.update_data(start_date=date)
        await state.set_state(Statistic.waiting_start_time)
        await callback.message.answer(
            "Введите время начала промежутка в формате hours:minutes"
        )


@router.message(StateFilter(Statistic.waiting_start_time))
async def input_end_date(message: types.CallbackQuery, state: FSMContext):
    await state.set_state(Statistic.waiting_end_date)
    start_time = message.text.strip()
    try:
        start_time = datetime.strptime(start_time, "%H:%M")
    except Exception as e:
        await message.answer("Время должно быть в формате hours:minutes")
        await state.set_state(UserStatus.admin)
        return
    user_data = await state.get_data()
    start_date = user_data["start_date"]
    start_date = datetime.combine(start_date, start_time.time())
    await state.update_data(start_date=start_date)

    calendar, cur_time = await get_calendar(message.from_user)
    await message.answer(
        "Выберите дату конца промежутка",
        reply_markup=await calendar.start_calendar(
            year=cur_time.year, month=cur_time.month
        ),
    )


@router.callback_query(
    StateFilter(Statistic.waiting_end_date),
    SimpleCalendarCallback.filter(),
)
async def input_end_time(
    callback: types.CallbackQuery,
    state: FSMContext,
    callback_data: CallbackData,
):
    calendar, cur_time = await get_calendar(callback.from_user)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        await state.update_data(end_date=date)
        await state.set_state(Statistic.waiting_end_time)
        await callback.message.answer(
            "Введите время конца промежутка в формате hours:minutes"
        )


@router.message(StateFilter(Statistic.waiting_end_time))
async def get_statistic(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    await state.clear()
    await state.update_data(user_id=user_data["user_id"])
    await state.update_data(status=user_data["status"])
    await state.set_state(UserStatus.admin)

    end_time = message.text.strip()
    try:
        end_time = datetime.strptime(end_time, "%H:%M")
    except Exception as e:
        await message.answer("Время должно быть в формате hours:minutes")
        return
    start_date = user_data["start_date"]
    end_date = user_data["end_date"]
    end_date = datetime.combine(end_date, end_time.time())

    stat = await db.get_statistic(start_date, end_date)
    if not stat:
        await message.answer("В данный период нет ни одной записи")
        return
    if isinstance(stat, str):
        await message.answer(stat)
        return

    ans = ""
    total_price = 0
    total_payouts = 0
    total_services = 0
    for worker in stat:
        total_price += worker["total_price"]
        total_payouts += worker["payout"]
        total_services += worker["total_services"]
        ans += (
            f"<i>{worker['name']}:</i>\n"
            f"Прибыль: {worker['total_price']}\n"
            f"Количество оказанных услуг: {worker['total_services']}\n"
            f"Выплаты сотруднику: {worker['payout']}\n\n"
        )
    ans += (
        f"<b>Общая прибыль:</b> {total_price}\n"
        f"<b>Общие выплаты:</b> {total_payouts}\n"
        f"<b>Количество услуг:</b> {total_services}\n"
    )
    await message.answer(ans, parse_mode="HTML")


@router.callback_query(F.data == "show clients")
async def show_users(callback: types.CallbackQuery):
    users = await db.find_all_users(1)
    info = "<b>Клиенты: (Стр. 1)</b>\n" + "\n".join(users)
    end = True if len(users) < 10 else False
    await callback.message.answer(
        info, reply_markup=generate_page_buttons(1, end), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("page:"))
async def send_new_page(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    users = await db.find_all_users(page)
    end = True if len(users) < 10 else False
    from bot import bot

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"<b>Клиенты: (Стр. {page})</b>\n" + "\n".join(users),
        reply_markup=generate_page_buttons(page, end),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "add user")
async def input_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UsersAdmin.waiting_for_name)
    await callback.message.answer("Введите имя")


@router.message(StateFilter(UsersAdmin.waiting_for_name))
async def input_login(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(UsersAdmin.waiting_for_login)
    await message.answer("Введите логин")


@router.message(StateFilter(UsersAdmin.waiting_for_login))
async def input_password(message: types.Message, state: FSMContext):
    await state.update_data(login=message.text.strip())
    await state.set_state(UsersAdmin.waiting_for_password)
    await message.answer("Введите пароль")


@router.message(StateFilter(UsersAdmin.waiting_for_password))
async def input_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await state.set_state(UsersAdmin.waiting_for_phone_number)
    await message.answer("Введите номер телефона(только цифры начиная с 8)")


@router.message(StateFilter(UsersAdmin.waiting_for_phone_number))
async def input_status(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()
    if len(phone_number.strip()) != 11:
        await state.set_state(UserStatus.admin)
        await message.answer(
            "Неправильный номер телефона, должно быть 11 символов"
        )
        return
    await state.set_state(UsersAdmin.waiting_for_status)
    await state.update_data(phone_number=phone_number)
    await message.answer(
        "Выберите статус пользователя", reply_markup=get_status()
    )


@router.callback_query(
    StateFilter(UsersAdmin.waiting_for_status),
    F.data.startswith("chosen_status:"),
)
async def add_user(callback: types.CallbackQuery, state: FSMContext):
    # Восстанавливаем state
    data = await state.get_data()
    await state.clear()
    await state.set_state(UserStatus.admin)
    await state.update_data(user_id=data["user_id"])
    await state.update_data(status=data["status"])

    # Добавляем пользователя
    data["chat_id"] = None
    data["status"] = callback.data.split(":")[1]
    res = await db.add_user(data)
    if "успешно" in res:
        await callback.message.answer("Пользователь добавлен")
    else:
        await callback.message.answer(res)


@router.callback_query(F.data == "delete user")
async def input_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UsersAdmin.waiting_for_name_to_delete)
    await callback.message.answer("Введите имя пользователя для удаления:")


@router.message(StateFilter(UsersAdmin.waiting_for_name_to_delete))
async def delete_user(message: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStatus.admin)
    name = message.text.strip()
    data = await state.get_data()
    res = await db.delete_user(name, data["user_id"])
    await message.answer(res)


@router.message()
async def not_handled_message(message: types.Message):
    await message.answer(
        "Я вас не понимаю, используйте кнопки или напишите /help"
    )
