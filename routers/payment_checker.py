from aiogram import Router, F, Bot
from aiogram.types import Message
from database import db_api
from config import POSTBACK_CHANNEL, ADMIN_OF_BOT_PERCENT
from database.db_models import PaymentStatus
from payments.payment_manager import PAYPAL_CLIENT
from translate_texts.translate import translate_text as _
from config import ADMIN_OF_CHANNEL_PERCENT, COURSE_USD
router = Router()


@router.channel_post(F.chat.id == POSTBACK_CHANNEL)
async def postback_channel(message: Message):
    if message.text.startswith('paypal'):
        return await paypal_checker(message.text, message.bot)
    payment_type, payment_uuid, amount = message.text.split(':')
    amount = float(amount)
    amount *= ADMIN_OF_CHANNEL_PERCENT/100

    if message.text.startswith('yoomoney'):
        amount = round(amount / COURSE_USD, 2)
        await check_payment(payment_uuid, amount, message.bot)

    elif message.text.startswith('cryptomus'):
        await check_payment(payment_uuid, amount, message.bot)


async def paypal_checker(data: str, bot: Bot):
    _, token, pay_id, payer_id = data.split(':')
    data = await PAYPAL_CLIENT.execute_payment(pay_id, payer_id)
    amount = float(data['transactions'][0]['amount']['total'])
    amount *= ADMIN_OF_CHANNEL_PERCENT / 100
    await check_payment(token, amount, bot)


async def check_payment(payment_uuid: str, amount: float, bot: Bot):
    payment = await db_api.check_payment(payment_uuid)
    await db_api.change_payment_status(payment_uuid, PaymentStatus.COMPLETED)

    if payment.status != PaymentStatus.COMPLETED.value:
        await notify_user_about_payment(bot, payment.user_id, payment_uuid)
        # await bot.send_message(
        #     payment.user_id,
        #     f'{payment_text} `{payment_uuid}` {was_paid}\n',
        #     parse_mode='markdownv2'
        # )

        await paid_percentages(payment.channel_id, amount, bot)
        # admin_user = await db_api.get_user_admin_by_channel_id(payment.channel_id)
        # amount = round(amount / COURSE_USD, 2)
        # await db_api.update_balance(admin_user.user_id, amount + admin_user.balance)
        # t = await _("Вам было зачислено", admin_user.user_id)
        # await bot.send_message(admin_user.user_id, f"{t} {amount}$")


async def notify_user_about_payment(bot: Bot, user_id: int, payment_uuid: str):
    payment_text = await _('Заявка', user_id)
    was_paid = await _('была оплачена', user_id)
    await bot.send_message(
        user_id,
        f'{payment_text} `{payment_uuid}` {was_paid}\n',
        parse_mode='markdownv2'
    )


async def paid_percentages(channel_id: int, amount: float, bot: Bot):
    admin_user = await db_api.get_user_admin_by_channel_id(channel_id)

    t = await _("Вам было зачислено", admin_user.user_id)
    await db_api.update_balance(admin_user.user_id, amount + admin_user.balance)
    await bot.send_message(admin_user.user_id, f"{t} {round(amount, 2)}$")

    if admin_user.pr_code:
        pr_id = await db_api.get_pr_id_by_code(admin_user.pr_code)
        pr_user = await db_api.get_pr(pr_id)
        if pr_user:
            u = await db_api.get_user(pr_id)
            pr_amount = round(amount/(ADMIN_OF_CHANNEL_PERCENT/100)*(ADMIN_OF_BOT_PERCENT/100)*(pr_user.percent/100), 4)
            await db_api.update_balance(pr_user.user_id, pr_amount + u.balance)
            await bot.send_message(
                pr_id,
                f"{t} {pr_amount}$"
            )
