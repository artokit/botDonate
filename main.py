import asyncio
from aiogram import Dispatcher, Bot
from config import TOKEN
from routers import user, admins
from payments import payment_checker

bot = Bot(TOKEN)
dp = Dispatcher()


async def main():
    dp.include_routers(admins.router, user.router)
    await dp.start_polling(bot)


loop = asyncio.new_event_loop()
tasks = asyncio.wait([loop.create_task(main()), loop.create_task(payment_checker.yoomoney_check(bot))])
# tasks = asyncio.wait([loop.create_task(main())])
loop.run_until_complete(tasks)
