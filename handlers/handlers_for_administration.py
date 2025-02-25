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
    get_interface_manage_services,
    get_service_col_to_change,
)
from keyboards.keyboards_for_clients import get_list_services
from utils.calendar import get_calendar
from utils.middlewares import SQLInjectionMiddleware
from utils.states import (
    SchedulerAdmin,
    UserStatus,
    WorkingTime,
    Statistic,
    UsersAdmin,
    Services,
)

router = Router()
router.message.middleware(SQLInjectionMiddleware())


@router.callback_query(F.data == "users")
async def show_managment_of_users(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление пользователями", reply_markup=get_interface_manage_users()
    )


@router.callback_query(F.data == "workers")
async def show_managment_of_workers(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление сотрудниками", reply_markup=get_interface_manage_workers()
    )


@router.callback_query(F.data == "schedule")
async def show_managment_of_schedule(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление расписанием", reply_markup=get_interface_manage_schedule()
    )


@router.callback_query(F.data == "services")
async def show_managment_of_services(callback: types.CallbackQuery):
    await callback.message.answer(
        "Управление услугами", reply_markup=get_interface_manage_services()
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
        "Выберите услугу:", reply_markup=await get_list_services()
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
    name = message.text.strip()
    if await db.check_existing(name=name):
        await message.answer("Данное имя занято, попробуйте другое")
        return
    await state.update_data(name=name)
    await state.set_state(UsersAdmin.waiting_for_login)
    await message.answer("Введите логин")


@router.message(StateFilter(UsersAdmin.waiting_for_login))
async def input_password(message: types.Message, state: FSMContext):
    login = message.text.strip()
    if await db.check_existing(login=login):
        await message.answer("Данный логин занят, попробуйте другой")
        await state.set_state(UserStatus.admin)
        return
    await state.update_data(login=login)
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


@router.callback_query(F.data == "show user info")
async def input_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UsersAdmin.waiting_for_name_to_show_info)
    await callback.message.answer("Введите имя пользователя")


@router.message(StateFilter(UsersAdmin.waiting_for_name_to_show_info))
async def show_info(message: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    await state.set_state(UserStatus.admin)
    name = message.text.strip()
    res = await db.show_user_info(name)
    if not res:
        await message.answer("Пользователя с таким именем не существует")
        return
    if isinstance(res, str):
        await message.answer(res)
        return

    password = "Скрыт"
    if res["id"] == user_id or res["status"] == "client":
        password = res["password"]
    status = "Клиент" if res["status"] == "client" else "Администратор"
    await message.answer(
        f"<b>Имя:</b> {name}\n"
        f"<b>Логин:</b> {res['login']}\n"
        f"<b>Пароль:</b> {password}\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Номер телефона:</b> {res['phone_number']}\n",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "list services admin")
async def show_services_admin(callback: types.CallbackQuery):
    services = await db.show_services()
    all_services = "Название - цена / выплата сотруднику в руб.\n"
    for service in services:
        all_services += (
            f"• <b>{service['service_name']}</b> - "
            f"{service['price']} / "
            f"{service['payout_worker']}\n"
        )
    await callback.message.answer(all_services, parse_mode="HTML")


@router.callback_query(F.data == "add service")
async def input_service_name_to_add(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(Services.waiting_for_service_name_to_add)
    await callback.message.answer("Введите название услуги")


@router.message(StateFilter(Services.waiting_for_service_name_to_add))
async def input_price_to_add(message: types.Message, state: FSMContext):
    await state.set_state(Services.waiting_for_price_to_add)
    service_name = message.text.strip()
    await state.update_data(service_name=service_name)
    await message.answer("Введите цену услуги в руб.")


@router.message(StateFilter(Services.waiting_for_price_to_add))
async def input_payout(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except Exception:
        await state.set_state(UserStatus.admin)
        await message.answer(
            "Неправильный формат цены, должно быть целое число"
        )
        return
    await state.update_data(price=price)
    await state.set_state(Services.waiting_for_payout_to_add)
    await message.answer("Введите выплату сотруднику в руб.")


@router.message(StateFilter(Services.waiting_for_payout_to_add))
async def add_service(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await state.set_state(UserStatus.admin)
    await state.update_data(user_id=data["user_id"])
    await state.update_data(status=data["status"])
    try:
        payout = int(message.text.strip())
    except Exception:
        await message.answer(
            "Неправильный формат выплаты, должно быть целое число"
        )
        return
    if data["price"] < payout:
        await message.answer(
            "Выплата сотруднику не может быть больше цены услуги"
        )
        return
    res = await db.add_service(data["service_name"], data["price"], payout)
    await message.answer(res)


@router.callback_query(F.data == "change serv price")
async def choose_service_change(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(Services.waiting_for_service_name_to_change)
    await callback.message.answer(
        "Выберите услугу для изменения", reply_markup=await get_list_services()
    )


@router.callback_query(
    StateFilter(Services.waiting_for_service_name_to_change),
    F.data.startswith("choose-service_"),
)
async def choose_service_col_change(
    callback: types.CallbackQuery, state: FSMContext
):
    service_name = callback.data.split("_", maxsplit=1)[1]
    await state.set_state(Services.waiting_for_service_col_to_change)
    await state.update_data(service_name=service_name)

    from bot import bot

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"Вы выбрали услугу: {service_name}",
        reply_markup=None,
    )
    await callback.message.answer(
        "Выберите поле для изменения", reply_markup=get_service_col_to_change()
    )


@router.callback_query(
    StateFilter(Services.waiting_for_service_col_to_change),
    F.data.startswith("service-col:"),
)
async def input_new_value(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Services.waiting_for_new_value_to_change)
    col = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(col=col)
    field = "Цена" if col == "price" else "Выплата сотруднику"
    from bot import bot

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"Вы выбрали поле: {field}",
        reply_markup=None,
    )
    await callback.message.answer("Введите новое значение в руб.")


@router.message(StateFilter(Services.waiting_for_new_value_to_change))
async def change_service(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await state.set_state(UserStatus.admin)
    await state.update_data(user_id=data["user_id"])
    await state.update_data(status=data["status"])

    try:
        new_value = int(message.text.strip())
    except Exception:
        await message.answer(
            "Неправильный формат нового значения, должно быть целое число"
        )
        return
    res = await db.change_service_info(
        data["service_name"], data["col"], new_value
    )
    await message.answer(res)


@router.callback_query(F.data == "delete service")
async def choose_service_delete(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.set_state(Services.waiting_for_service_name_to_delete)
    await callback.message.answer(
        "Выберите услугу для удаления", reply_markup=await get_list_services()
    )


@router.callback_query(
    StateFilter(Services.waiting_for_service_name_to_delete),
    F.data.startswith("choose-service_"),
)
async def delete_service(callback: types.CallbackQuery, state: FSMContext):
    service_name = callback.data.split("_", maxsplit=1)[1]
    res = await db.delete_service(service_name)
    await state.set_state(UserStatus.admin)
    from bot import bot

    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"{service_name}: {res}",
        reply_markup=None,
    )


@router.message()
async def not_handled_message(message: types.Message):
    await message.answer(
        "Я вас не понимаю, используйте кнопки или напишите /help"
    )
