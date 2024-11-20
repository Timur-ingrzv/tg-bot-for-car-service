import asyncio
import config
from aiogram import Bot, Dispatcher
from aiogram.filters.command import Command, Message

from handlers import handlers_unauthorized_user, handlers_administration_user, handlers_clients_user
from keyboards import keyboards_unauthorized_user


# Объект бота
bot = Bot(token=config.TOKEN)
# Диспетчер
dp = Dispatcher()

# Запуск процесса поллинга новых апдейтов
async def main():
    dp.include_routers(handlers_unauthorized_user.router, handlers_administration_user.router)
    await dp.start_polling(bot)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(f"Добро пожаловать в автосервис {config.CAR_SERVICE_NAME}\n",
                         reply_markup=keyboards_unauthorized_user.get_start_keyboard())

if __name__ == "__main__":
    asyncio.run(main())
