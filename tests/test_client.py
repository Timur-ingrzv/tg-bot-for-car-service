import pytest
import asyncio
from datetime import datetime, date, timedelta, time
from unittest.mock import AsyncMock, patch, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, Message, User, Chat
from aiogram.methods import SendMessage, EditMessageText

from handlers.handlers_for_clients import (
    input_date_to_add_schedule,
    input_time_to_add_schedule,
    input_service_name,
    add_schedule,
    input_date_for_scheduler,
    show_schedule
)
from utils.states import SchedulerClient, UserStatus
from handlers.handlers_for_clients import SimpleCalendarCallback

@pytest.fixture
def user():
    return User(id=123, first_name="Test", is_bot=False)


@pytest.fixture
def chat():
    return Chat(id=456, type="private")

@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(chat_id=456, user_id=123, bot_id=42)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
def message(user, chat):
    def _message(text: str):
        return Message(
            message_id=1011,
            chat=chat,
            from_user=user,
            date=datetime.now(),
            text=text
        )
    return _message


@pytest.fixture
def callback_query():
    def _factory(data: str):
        user = User.model_construct(
            id=123,
            first_name="Test",
            is_bot=False,
            language_code="ru",
        )

        return CallbackQuery.model_construct(
            id="1",
            from_user=user,
            message=Message.model_construct(
                message_id=1,
                chat=Chat.model_construct(id=456, type="private"),
                date=datetime.now(),
                text="some text"
            ),
            chat_instance="ci",
            data=data
        )
    return _factory


'''Тестирование записи на услугу'''
@pytest.mark.asyncio
async def test_input_date_to_add_schedule(callback_query, fsm_context):
    now = datetime.now() + timedelta(days=1)
    with patch("utils.calendar.get_calendar", new_callable=AsyncMock) as mock_calendar, \
            patch.object(Message, "answer", new_callable=AsyncMock) as mock_answer:
        mock_calendar.return_value = (AsyncMock(), now)

        callback = callback_query("sign up for service")

        await input_date_to_add_schedule(callback, fsm_context)

        # Проверяем, что состояние установлено
        state = await fsm_context.get_state()
        assert state == SchedulerClient.waiting_for_date_to_add_schedule

        # Проверяем, что отправка сообщения происходила
        args, kwargs = mock_answer.await_args
        assert args[0] == "Выберите желаемую дату"


@pytest.mark.asyncio
async def test_input_time_to_add_schedule(callback_query, fsm_context):
    calendar_mock = AsyncMock()
    now = datetime.now() + timedelta(days=1)
    calendar_mock.process_selection.return_value = (True, date.today() + timedelta(days=1))
    with patch("utils.calendar.get_calendar", new_callable=AsyncMock) as mock_calendar, \
            patch.object(Message, "answer", new_callable=AsyncMock) as mock_msg_answer, \
            patch.object(Message, "delete_reply_markup", new_callable=AsyncMock) as mock_delete_markup:
        mock_calendar.return_value = (calendar_mock, date.today())
        callback_data = SimpleCalendarCallback(act="DAY", year=now.year, month=now.month, day=now.day)
        callback = callback_query(callback_data.pack())

        await fsm_context.set_state(SchedulerClient.waiting_for_date_to_add_schedule)

        await input_time_to_add_schedule(callback, fsm_context, callback_data)

        # Проверим, что сообщение было отправлено
        mock_msg_answer.assert_awaited_with("Введите желаемое время - час дня")

        # Проверим, что состояние изменилось
        state = await fsm_context.get_state()
        assert state == SchedulerClient.waiting_for_time_to_add_schedule


@pytest.mark.asyncio
async def test_input_service_name_valid_time(message, fsm_context):
    valid_hour = datetime.now().hour + 1
    await fsm_context.set_state(SchedulerClient.waiting_for_time_to_add_schedule)
    await fsm_context.update_data(date=date.today())

    msg = message(str(valid_hour))

    with patch("keyboards.keyboards_for_clients.get_list_services", new_callable=AsyncMock) as mock_services, \
            patch.object(Message, "answer", new_callable=AsyncMock) as mock_msg_answer:
        mock_services.return_value = AsyncMock()

        await input_service_name(msg, fsm_context)

        fsm_state = await fsm_context.get_state()
        assert fsm_state == SchedulerClient.waiting_for_service_name_to_add_schedule
        args, kwargs = mock_msg_answer.await_args
        assert args[0] == "Выберите услугу"


@pytest.mark.asyncio
async def test_input_service_name_invalid_time(message, fsm_context):
    await fsm_context.set_state(SchedulerClient.waiting_for_time_to_add_schedule)
    await fsm_context.update_data(date=date.today())

    msg = message('abc')

    with patch("keyboards.keyboards_for_clients.get_list_services", new_callable=AsyncMock) as mock_services, \
            patch.object(Message, "answer", new_callable=AsyncMock) as mock_msg_answer:
        mock_services.return_value = AsyncMock()

        await input_service_name(msg, fsm_context)

        fsm_state = await fsm_context.get_state()
        args, kwargs = mock_msg_answer.await_args
        assert args[0] == "Неправильный формат времени - введите число от 0 до 23"


@pytest.mark.asyncio
async def test_add_schedule(callback_query, fsm_context):
    await fsm_context.set_state(SchedulerClient.waiting_for_service_name_to_add_schedule)
    test_datetime = datetime.now() + timedelta(days=1)
    await fsm_context.update_data(date=test_datetime, user_id=123, status="active")

    callback = callback_query("choose-service_Шиномонтаж")

    with patch("database.methods.db.add_schedule", new_callable=AsyncMock) as mock_add_schedule, \
            patch("bot.bot.edit_message_text", new_callable=AsyncMock) as mock_edit, \
            patch.object(Message, "answer", new_callable=AsyncMock) as mock_cb_answer:
        mock_add_schedule.return_value = "Расписание добавлено"

        await add_schedule(callback, fsm_context)

        mock_edit.assert_called_once_with(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Вы выбрали услугу <b>Шиномонтаж</b>",
            reply_markup=None,
            parse_mode="HTML",
        )

        callback.message.answer.assert_called_with("Расписание добавлено")

        fsm_state = await fsm_context.get_state()
        assert fsm_state == UserStatus.client

        data = await fsm_context.get_data()
        assert data["user_id"] == 123
        assert data["status"] == "active"


'''Тестирование просмотра расписания'''
@pytest.mark.asyncio
async def test_input_date_for_scheduler(callback_query, fsm_context):
    with patch("utils.calendar.get_calendar", new_callable=AsyncMock) as mock_calendar, \
         patch.object(Message, "answer", new_callable=AsyncMock):

        calendar_mock = AsyncMock()
        now = datetime.now() + timedelta(days=1)
        mock_calendar.return_value = (calendar_mock, now)

        callback = callback_query("show scheduler for client")
        await input_date_for_scheduler(callback, fsm_context)

        state = await fsm_context.get_state()
        assert state == SchedulerClient.waiting_for_date_to_show_schedule


@pytest.mark.asyncio
async def test_show_schedule(callback_query, fsm_context):
    with patch("utils.calendar.get_calendar", new_callable=AsyncMock) as mock_calendar, \
         patch("database.methods.db.find_free_slots", new_callable=AsyncMock) as mock_find_slots, \
         patch.object(Message, "answer", new_callable=AsyncMock), \
         patch.object(Message, "delete_reply_markup", new_callable=AsyncMock), \
         patch.object(CallbackQuery, "answer", new_callable=AsyncMock):

        date_today = datetime.today().date() + timedelta(days=1)
        selected_date = datetime.combine(date_today, time(0, 0))
        calendar_mock = AsyncMock()
        calendar_mock.process_selection.return_value = (True, selected_date)

        mock_calendar.return_value = (calendar_mock, date_today)
        mock_find_slots.return_value = ["10:00", "11:00"]

        callback_data = SimpleCalendarCallback(act="DAY", year=selected_date.year, month=selected_date.month, day=selected_date.day)
        callback = callback_query(callback_data.pack())

        await fsm_context.set_state(SchedulerClient.waiting_for_date_to_show_schedule)

        await show_schedule(callback, fsm_context, callback_data)

        assert await fsm_context.get_state() == UserStatus.client
        mock_find_slots.assert_awaited_with(selected_date)

