import asyncio
from aiogram.fsm.context import FSMContext
import config
from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command, Message

from handlers import (
    handlers_for_unauthorized,
    handlers_for_administration,
    handlers_for_clients,
)
from keyboards import keyboards_for_unauthorized
from keyboards.keyboards_for_administration import get_interface_for_admin
from keyboards.keyboards_for_clients import get_interface_for_client
from utils.states import UserStatus

# Объект бота
bot = Bot(token=config.BOT_TOKEN)
# Диспетчер
dp = Dispatcher()


# Запуск процесса поллинга новых апдейтов
async def main():
    dp.include_routers(
        handlers_for_unauthorized.router,
        handlers_for_clients.router,
        handlers_for_administration.router,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


@dp.message(Command("start"))
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.set_state(UserStatus.unauthorized)
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Добро пожаловать в автосервис {config.CAR_SERVICE_NAME}\n",
        reply_markup=keyboards_for_unauthorized.get_start_keyboard(),
    )


@dp.message(Command("help"))
async def helper(message: Message, state: FSMContext, bot: Bot):
    cur_state = await state.get_state()
    if cur_state == UserStatus.admin.state:
        await message.answer(
            "Доступные опции для администрации",
            reply_markup=get_interface_for_admin(),
        )
    elif cur_state == UserStatus.client.state:
        await message.answer(
            "Доступные опции для клиента",
            reply_markup=get_interface_for_client(),
        )
    else:
        await cmd_start(message, bot, state)


if __name__ == "__main__":
    asyncio.run(main())
