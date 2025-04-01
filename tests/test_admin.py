import pytest
from unittest.mock import AsyncMock, patch
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, Chat, User
from datetime import datetime, timedelta
from utils.states import (
    WorkingTime,
    UserStatus,
    SchedulerAdmin,
    Statistic,
    UsersAdmin,
    Services,
)
from handlers.handlers_for_administration import (
    input_name_to_delete,
    input_date_to_delete,
    delete_scheduler,
    show_users,
    send_new_page,
    input_worker_name,
    show_working_time,
    get_statistic,
    change_working_time,
    show_info,
    add_service,
    choose_service_col_change,
)
from datetime import time


@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(chat_id=456, user_id=123, bot_id=42)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
def callback_query():
    def _factory(data: str):
        user = User.model_construct(
            id=123, first_name="Admin", is_bot=False, language_code="ru"
        )
        return CallbackQuery.model_construct(
            id="1",
            from_user=user,
            data=data,
            chat_instance="ci",
            message=Message.model_construct(
                message_id=1,
                date=datetime.now(),
                chat=Chat.model_construct(id=456, type="private"),
                text="",
            ),
        )

    return _factory


@pytest.fixture
def message():
    user = User.model_construct(
        id=123, is_bot=False, first_name="Test", language_code="ru"
    )
    chat = Chat.model_construct(id=456, type="private")
    return Message.model_construct(
        message_id=1, from_user=user, chat=chat, date=None, text="Михаил"
    )


"""Тестирование просмотра пользователей"""
@pytest.mark.asyncio
async def test_show_users(callback_query):
    callback = callback_query("show clients")
    with patch(
        "database.methods.db.find_all_users", new_callable=AsyncMock
    ) as mock_find, patch(
        "handlers.handlers_for_administration.generate_page_buttons",
        return_value="mock_kb",
    ), patch.object(
        Message, "answer", new_callable=AsyncMock
    ):
        mock_find.return_value = ["User 1", "User 2"]

        await show_users(callback)

        mock_find.assert_awaited_with(1)
        callback.message.answer.assert_awaited_with(
            "<b>Клиенты: (Стр. 1)</b>\nUser 1\nUser 2",
            reply_markup="mock_kb",
            parse_mode="HTML",
        )


@pytest.mark.asyncio
async def test_send_new_page(callback_query):
    callback = callback_query("page:3")
    with patch(
        "database.methods.db.find_all_users", new_callable=AsyncMock
    ) as mock_find, patch(
        "handlers.handlers_for_administration.generate_page_buttons",
        return_value="mock_kb",
    ), patch(
        "main.bot.edit_message_text", new_callable=AsyncMock
    ) as mock_edit:
        mock_find.return_value = [f"User {i}" for i in range(10)]
        await send_new_page(callback)
        mock_find.assert_awaited_with(3)
        mock_edit.assert_awaited_with(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="<b>Клиенты: (Стр. 3)</b>\n"
            + "\n".join(mock_find.return_value),
            reply_markup="mock_kb",
            parse_mode="HTML",
        )


"""Тестирование просмотра информации о сотрудниках"""
@pytest.mark.asyncio
async def test_input_worker_name(callback_query, fsm_context):
    callback = callback_query("show working time for worker")
    with patch.object(Message, "answer", new_callable=AsyncMock):
        await input_worker_name(callback, fsm_context)

        state = await fsm_context.get_state()
        assert state == WorkingTime.waiting_worker_name_to_show
        callback.message.answer.assert_awaited_with("Введите имя работника")


@pytest.mark.asyncio
async def test_show_working_time_error(message, fsm_context):
    await fsm_context.set_state(WorkingTime.waiting_worker_name_to_show)
    with patch(
        "database.methods.db.show_working_time", new_callable=AsyncMock
    ) as mock_db, patch.object(Message, "answer", new_callable=AsyncMock):
        mock_db.return_value = "Работник не найден"
        await show_working_time(message, fsm_context)

        state = await fsm_context.get_state()
        assert state == UserStatus.admin
        message.answer.assert_awaited_with("Работник не найден")


@pytest.mark.asyncio
async def test_show_working_time_with_schedule(message, fsm_context):
    await fsm_context.set_state(WorkingTime.waiting_worker_name_to_show)
    with patch(
        "database.methods.db.show_working_time", new_callable=AsyncMock
    ) as mock_db, patch.object(Message, "answer", new_callable=AsyncMock):
        mock_db.return_value = [
            {"day_week": 0, "time_start": time(9, 0), "time_end": time(17, 0)},
            {
                "day_week": 2,
                "time_start": time(10, 0),
                "time_end": time(15, 0),
            },
        ]
        await show_working_time(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == UserStatus.admin

        expected = (
            "<b>Михаил</b>\n"
            "<b>ПН:</b> 09:00 - 17:00\n"
            "<b>ВТ:</b> Не работает\n"
            "<b>СР:</b> 10:00 - 15:00\n"
            "<b>ЧТ:</b> Не работает\n"
            "<b>ПТ:</b> Не работает\n"
            "<b>СБ:</b> Не работает\n"
            "<b>ВС:</b> Не работает\n"
        )
        message.answer.assert_awaited_with(expected, parse_mode="HTML")


@pytest.mark.asyncio
async def test_input_name_to_delete(callback_query, fsm_context):
    callback = callback_query("delete record")
    with patch.object(Message, "answer", new_callable=AsyncMock):
        await input_name_to_delete(callback, fsm_context)
        assert (
            await fsm_context.get_state()
            == SchedulerAdmin.waiting_for_name_to_delete
        )
        callback.message.answer.assert_awaited_with(
            "Введите имя клиента или работника"
        )


@pytest.mark.asyncio
async def test_input_date_to_delete(message, fsm_context):
    await fsm_context.set_state(SchedulerAdmin.waiting_for_name_to_delete)
    now = datetime.now() + timedelta(days=1)
    with patch(
        "utils.calendar_tg.get_calendar", new_callable=AsyncMock
    ) as mock_calendar, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        calendar_mock = AsyncMock()
        mock_calendar.return_value = (calendar_mock, now)
        calendar_mock.start_calendar.return_value = "mock_kb"
        await input_date_to_delete(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == SchedulerAdmin.waiting_for_date_to_delete
        data = await fsm_context.get_data()
        assert data["name"] == "Михаил"
        args, kwargs = mock_answer.await_args
        assert args[0] == "Выберите дату для удаления записи"


@pytest.mark.asyncio
async def test_delete_scheduler_success(message, fsm_context):
    future_date = datetime.today().date() + timedelta(days=1)
    await fsm_context.set_state(SchedulerAdmin.waiting_for_time_to_delete)
    await fsm_context.update_data(
        {
            "date": future_date,
            "name": "Иван",
            "user_id": 123,
            "status": "admin",
        }
    )

    message = message.copy(update={"text": str(datetime.now().hour + 1)})
    with patch(
        "database.methods.db.delete_schedule", new_callable=AsyncMock
    ) as mock_delete, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_delete.return_value = "Запись удалена"
        await delete_scheduler(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == UserStatus.admin
        message.answer.assert_awaited_with("Запись удалена")


@pytest.mark.asyncio
async def test_delete_scheduler_invalid_hour(message, fsm_context):
    await fsm_context.set_state(SchedulerAdmin.waiting_for_time_to_delete)
    await fsm_context.update_data({"date": datetime.today().date()})
    message = message.copy(update={"text": "25"})
    with patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        await delete_scheduler(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == SchedulerAdmin.waiting_for_time_to_delete
        mock_answer.assert_awaited_with(
            "Время должно быть целое число в диапазоне от 0 до 23"
        )


"""Тестирование статистики"""
@pytest.mark.asyncio
async def test_get_statistic_success(message, fsm_context):
    start = datetime.today()
    end = start + timedelta(days=1)
    await fsm_context.set_state(Statistic.waiting_end_time)
    await fsm_context.update_data(
        {
            "start_date": start,
            "end_date": end,
            "user_id": 123,
            "status": "admin",
        }
    )
    fake_stat = [
        {
            "name": "Иван",
            "total_price": 1000,
            "total_services": 5,
            "payout": 400,
        },
        {
            "name": "Мария",
            "total_price": 2000,
            "total_services": 7,
            "payout": 800,
        },
    ]
    message = message.copy(update={"text": "11:00"})
    with patch(
        "database.methods.db.get_statistic", new_callable=AsyncMock
    ) as mock_stat, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_stat.return_value = fake_stat
        await get_statistic(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == UserStatus.admin

        expected_text = (
            "<i>Иван:</i>\nПрибыль: 1000\nКоличество оказанных услуг: 5\nВыплаты сотруднику: 400\n\n"
            "<i>Мария:</i>\nПрибыль: 2000\nКоличество оказанных услуг: 7\nВыплаты сотруднику: 800\n\n"
            "<b>Общая прибыль:</b> 3000\n"
            "<b>Общие выплаты:</b> 1200\n"
            "<b>Количество услуг:</b> 12\n"
        )
        mock_answer.assert_awaited_with(expected_text, parse_mode="HTML")


@pytest.mark.asyncio
async def test_get_statistic_invalid_time_format(message, fsm_context):
    await fsm_context.set_state(Statistic.waiting_end_time)
    await fsm_context.update_data(
        {
            "start_date": datetime.today(),
            "end_date": datetime.today(),
            "user_id": 1,
            "status": "admin",
        }
    )
    message = message.copy(update={"text": "abc"})
    with patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        await get_statistic(message, fsm_context)
        mock_answer.assert_awaited_with(
            "Время должно быть в формате hours:minutes"
        )


@pytest.mark.asyncio
async def test_get_statistic_empty_result(message, fsm_context):
    message = message.copy(update={"text": "11:00"})
    await fsm_context.set_state(Statistic.waiting_end_time)
    await fsm_context.update_data(
        {
            "start_date": datetime.now() - timedelta(days=1),
            "end_date": datetime.now().date(),
            "user_id": 1,
            "status": "admin",
        }
    )
    with patch(
        "database.methods.db.get_statistic", new_callable=AsyncMock
    ) as mock_stat, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_stat.return_value = []
        await get_statistic(message, fsm_context)
        mock_answer.assert_awaited_with("В данный период нет ни одной записи")


@pytest.mark.asyncio
async def test_get_statistic_error(message, fsm_context):
    message = message.copy(update={"text": "11:00"})
    await fsm_context.set_state(Statistic.waiting_end_time)
    await fsm_context.update_data(
        {
            "start_date": datetime.now() - timedelta(days=1),
            "end_date": datetime.now().date(),
            "user_id": 1,
            "status": "admin",
        }
    )
    with patch(
        "database.methods.db.get_statistic", new_callable=AsyncMock
    ) as mock_stat, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_stat.return_value = "Ошибка соединения"
        await get_statistic(message, fsm_context)
        mock_answer.assert_awaited_with("Ошибка соединения")


"""Тестирование изменения рабочего времени"""


@pytest.mark.asyncio
async def test_change_working_time_delete(message, fsm_context):
    await fsm_context.set_state(WorkingTime.waiting_time)
    await fsm_context.update_data(
        {"user_id": 123, "status": "admin", "worker_id": 5, "weekday": 1}
    )
    message = message.copy(update={"text": "0"})
    with patch(
        "database.methods.db.delete_working_time", new_callable=AsyncMock
    ) as mock_del, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_del.return_value = "Удалено"
        await change_working_time(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == UserStatus.admin
        mock_del.assert_awaited_with(5, 1)
        mock_answer.assert_awaited_with("Удалено")


@pytest.mark.asyncio
async def test_change_working_time_add(message, fsm_context):
    await fsm_context.set_state(WorkingTime.waiting_time)
    await fsm_context.update_data(
        {"user_id": 123, "status": "admin", "worker_id": 7, "weekday": 2}
    )
    message = message.copy(update={"text": "9-18"})
    with patch(
        "database.methods.db.add_working_time", new_callable=AsyncMock
    ) as mock_add, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_add.return_value = "Добавлено"
        await change_working_time(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == UserStatus.admin
        mock_add.assert_awaited_with(7, time(9), time(18), 2)
        mock_answer.assert_awaited_with("Добавлено")


@pytest.mark.asyncio
async def test_change_working_time_invalid_format(
    message, fsm_context, caplog
):
    await fsm_context.set_state(WorkingTime.waiting_time)
    await fsm_context.update_data(
        {"user_id": 123, "status": "admin", "worker_id": 7, "weekday": 3}
    )
    message = message.copy(update={"text": "abc"})
    with patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        await change_working_time(message, fsm_context)
        state = await fsm_context.get_state()
        assert state == WorkingTime.waiting_time
        mock_answer.assert_awaited_with("Неправильный формат времени")


"""Тестирование просмотра информации об одном пользователе"""


@pytest.mark.asyncio
async def test_show_info_user_not_found(message, fsm_context):
    await fsm_context.set_state(UsersAdmin.waiting_for_name_to_show_info)
    await fsm_context.update_data(user_id=222)
    with patch(
        "database.methods.db.show_user_info", new_callable=AsyncMock
    ) as mock_db, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_db.return_value = None
        await show_info(message, fsm_context)
        mock_answer.assert_awaited_with(
            "Пользователя с таким именем не существует"
        )


@pytest.mark.asyncio
async def test_show_info_db_returns_string(message, fsm_context):
    await fsm_context.set_state(UsersAdmin.waiting_for_name_to_show_info)
    await fsm_context.update_data(user_id=222)
    with patch(
        "database.methods.db.show_user_info", new_callable=AsyncMock
    ) as mock_db, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_db.return_value = "Ошибка подключения к базе"
        await show_info(message, fsm_context)
        mock_answer.assert_awaited_with("Ошибка подключения к базе")


@pytest.mark.asyncio
async def test_show_info_self_info(message, fsm_context):
    await fsm_context.set_state(UsersAdmin.waiting_for_name_to_show_info)
    await fsm_context.update_data(user_id=222)
    with patch(
        "database.methods.db.show_user_info", new_callable=AsyncMock
    ) as mock_db, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_db.return_value = {
            "id": 222,
            "login": "admin1",
            "password": "adminpass",
            "status": "admin",
            "phone_number": "+79991112233",
        }
        await show_info(message, fsm_context)
        expected = (
            "<b>Имя:</b> Михаил\n"
            "<b>Логин:</b> admin1\n"
            "<b>Пароль:</b> adminpass\n"
            "<b>Статус:</b> Администратор\n"
            "<b>Номер телефона:</b> +79991112233\n"
        )
        mock_answer.assert_awaited_with(expected, parse_mode="HTML")


@pytest.mark.asyncio
async def test_show_info_other_admin(message, fsm_context):
    await fsm_context.set_state(UsersAdmin.waiting_for_name_to_show_info)
    await fsm_context.update_data(user_id=999)
    with patch(
        "database.methods.db.show_user_info", new_callable=AsyncMock
    ) as mock_db, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_db.return_value = {
            "id": 222,
            "login": "admin2",
            "password": "hiddenpass",
            "status": "admin",
            "phone_number": "+70000000000",
        }
        await show_info(message, fsm_context)
        expected = (
            "<b>Имя:</b> Михаил\n"
            "<b>Логин:</b> admin2\n"
            "<b>Пароль:</b> Скрыт\n"
            "<b>Статус:</b> Администратор\n"
            "<b>Номер телефона:</b> +70000000000\n"
        )
        mock_answer.assert_awaited_with(expected, parse_mode="HTML")


@pytest.mark.asyncio
async def test_show_info_client(message, fsm_context):
    await fsm_context.set_state(UsersAdmin.waiting_for_name_to_show_info)
    await fsm_context.update_data(user_id=999)
    with patch(
        "database.methods.db.show_user_info", new_callable=AsyncMock
    ) as mock_db, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_db.return_value = {
            "id": 333,
            "login": "client1",
            "password": "clientpass",
            "status": "client",
            "phone_number": "+78887776655",
        }
        await show_info(message, fsm_context)
        expected = (
            "<b>Имя:</b> Михаил\n"
            "<b>Логин:</b> client1\n"
            "<b>Пароль:</b> clientpass\n"
            "<b>Статус:</b> Клиент\n"
            "<b>Номер телефона:</b> +78887776655\n"
        )
        message.answer.assert_awaited_with(expected, parse_mode="HTML")


"""Тестирование добавления услуги"""
@pytest.mark.asyncio
async def test_add_service_invalid_format(message, fsm_context):
    await fsm_context.set_state(Services.waiting_for_payout_to_add)
    await fsm_context.update_data(
        {
            "user_id": 123,
            "status": "admin",
            "price": 1000,
            "service_name": "Стрижка",
        }
    )
    with patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        message = message.copy(update={"text": "abc"})
        await add_service(message, fsm_context)
        mock_answer.assert_awaited_with(
            "Неправильный формат выплаты, должно быть целое число"
        )


@pytest.mark.asyncio
async def test_add_service_payout_too_high(message, fsm_context):
    await fsm_context.set_state(Services.waiting_for_payout_to_add)
    await fsm_context.update_data(
        {
            "user_id": 123,
            "status": "admin",
            "price": 500,
            "service_name": "Массаж",
        }
    )
    with patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        message = message.copy(update={"text": "600"})
        await add_service(message, fsm_context)
        mock_answer.assert_awaited_with(
            "Выплата сотруднику не может быть больше цены услуги"
        )


@pytest.mark.asyncio
async def test_add_service_success(message, fsm_context):
    await fsm_context.set_state(Services.waiting_for_payout_to_add)
    await fsm_context.update_data(
        {
            "user_id": 123,
            "status": "admin",
            "price": 1200,
            "service_name": "Шиномонтаж",
        }
    )
    message = message.copy(update={"text": "400"})
    with patch(
        "database.methods.db.add_service", new_callable=AsyncMock
    ) as mock_add, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        mock_add.return_value = "Услуга добавлена"
        await add_service(message, fsm_context)
        mock_add.assert_awaited()
        mock_answer.assert_awaited_with("Услуга добавлена")
        mock_add.assert_awaited_with("Шиномонтаж", 1200, 400)
        state = await fsm_context.get_state()
        assert state == UserStatus.admin


@pytest.mark.asyncio
async def test_choose_service_col_change(callback_query, fsm_context):
    await fsm_context.set_state(Services.waiting_for_service_name_to_change)
    callback = callback_query("choose-service_Шиномонтаж")
    with patch(
        "keyboards.keyboards_for_administration.get_service_col_to_change",
        return_value="mock_kb",
    ), patch(
        "main.bot.edit_message_text", new_callable=AsyncMock
    ) as mock_edit, patch.object(
        Message, "answer", new_callable=AsyncMock
    ) as mock_answer:
        await choose_service_col_change(callback, fsm_context)
        # Проверка состояния и сохранённых данных
        state = await fsm_context.get_state()
        assert state == Services.waiting_for_service_col_to_change

        data = await fsm_context.get_data()
        assert data["service_name"] == "Шиномонтаж"

        # Проверка вызовов
        mock_edit.assert_awaited_with(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Вы выбрали услугу: Шиномонтаж",
            reply_markup=None,
        )
        args, kwargs = mock_answer.await_args
        assert args[0] == "Выберите поле для изменения"
