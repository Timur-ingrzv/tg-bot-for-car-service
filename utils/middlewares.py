from aiogram import BaseMiddleware, types, Dispatcher
from aiogram.fsm.context import FSMContext

from keyboards.keyboards_for_unauthorized import get_start_keyboard


FORBIDDEN_WORDS = ["insert", "select", "drop", "update"]


class MessageLengthMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.max_length = 40
        self.min_length = 4

    async def __call__(self, handler, event: types.Message, data: dict):
        fsm_context: FSMContext = data.get("fsm_context")
        if (
            len(event.text.strip()) > self.max_length
            or len(event.text.strip()) < 3
        ):
            if fsm_context:
                await fsm_context.clear()
            await event.answer(
                text=f"Сообщение неправильной длины, должно быть от {self.min_length} "
                f"до {self.max_length} символов.",
                reply_markup=get_start_keyboard(),
            )
            return
        return await handler(event, data)


class SQLInjectionMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(self, handler, event: types.Message, data: dict):
        if any(word.lower() in FORBIDDEN_WORDS for word in event.text.split()):
            await event.answer(text=f"Сообщение содержит запрещенные слова")
            return
        return await handler(event, data)
