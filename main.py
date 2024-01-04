import asyncio
from aiogram import Dispatcher, Bot
from config import TOKEN
from routers import user, admins, payment_checker, creator, prs
# from translate_texts import get_texts

bot = Bot(TOKEN)
dp = Dispatcher()


async def main():
    dp.include_routers(admins.router, user.router, payment_checker.router, creator.router, prs.router)
    print(await bot.get_me())
    await dp.start_polling(bot)


loop = asyncio.new_event_loop()
tasks = asyncio.wait([loop.create_task(main())])
loop.run_until_complete(tasks)
