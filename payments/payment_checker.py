import asyncio
from logs import logger
from aiogram import Bot
import db_api
from db_models import PaymentType, PaymentStatus
from payments.payment_manager import YOOMONEY_CLIENT
from translate_texts.translate import translate_text as _

# Переделать под запуск как отдельного файла или потока


async def yoomoney_check(bot: Bot):
    while True:
        await asyncio.sleep(2)
        active_payments = await db_api.get_active_payments_by_type(PaymentType.YOOMONEY)
        for payment in active_payments:
            try:
                status = YOOMONEY_CLIENT.check_payment(label=payment.payment_uuid, time=payment.time)
            except Exception as e:
                logger.error(f'YOOMONEY checker | {payment.payment_uuid} | ' + str(e))
                continue

            if status.value != payment.status:
                await db_api.change_payment_status(payment.payment_uuid, status)

            if status == PaymentStatus.COMPLETED:
                try:
                    await bot.send_message(payment.user_id, await _('Ваш платёж был подтверждён!', payment.user_id))
                except Exception as e:
                    print(1)
                    logger.error(f'User YOOMONEY Payment sender | {payment.user_id} | {str(e)}')

            if status == PaymentStatus.CANCELLED:
                await bot.send_message(payment.user_id, await _('Мы так и не дождались вашей оплаты :(', payment.user_id))
