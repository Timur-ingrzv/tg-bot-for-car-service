import asyncio
import config
from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command, Message

from handlers import (
    handlers_for_unauthorized,
    handlers_for_administration,
    handlers_for_clients,
)
from keyboards import keyboards_for_unauthorized


# Объект бота
bot = Bot(token=config.BOT_TOKEN)
# Диспетчер
dp = Dispatcher()


# Запуск процесса поллинга новых апдейтов
async def main():
    dp.include_routers(
        handlers_for_unauthorized.router, handlers_for_administration.router
    )
    await dp.start_polling(bot)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"Добро пожаловать в автосервис {config.CAR_SERVICE_NAME}\n",
        reply_markup=keyboards_for_unauthorized.get_start_keyboard(),
    )


if __name__ == "__main__":
    asyncio.run(main())
