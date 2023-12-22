import time
import uuid
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
import db_api
import keyboards
from db_models import Payment, PaymentStatus, PaymentType
from routers.admins import hi_admin
from aiogram import F
from payments.payment_manager import YOOMONEY_CLIENT, PAYPAL_CLIENT
from translate_texts.translate import translate_text as _


class UserPay(StatesGroup):
    enter_amount = State()


router = Router()


@router.message(Command('start'))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await db_api.add_user(message.chat.id, message.from_user.username)
    user = await db_api.get_user(message.chat.id)

    if message.text == '/start':
        if not user.lang:
            return await message.answer('Choice your language', reply_markup=keyboards.language.as_markup())

        return await hi_admin(message)

    await donate(message)


async def donate(message: Message):
    m = message.text
    m = m.split(' ')
    id_channel = int(m[1])

    channel = await db_api.get_channel_by_id(id_channel)
    kw = {
        'caption': channel.hello_text_content,
        'reply_markup': (await keyboards.get_transfer_keyboard(message.chat.id, id_channel)).as_markup(),
        'parse_mode': 'markdownv2'
    }

    if channel.photo:
        return await message.answer_photo(channel.photo, **kw)

    if channel.video:
        return await message.answer_video(channel.video, **kw)

    return await message.answer(
        text=channel.hello_text_content,
        reply_markup=(await keyboards.get_transfer_keyboard(message.chat.id, id_channel)).as_markup(),
        parse_mode='markdownv2'
    )


@router.callback_query(F.data.startswith('pay'))
async def wal(call: CallbackQuery, state: FSMContext):
    arr = call.data.split(':')
    type_of_payment, channel_id = arr[1], int(arr[2])
    await state.set_state(UserPay.enter_amount)
    await state.set_data({'channel_id': channel_id, 'type_of_payment': type_of_payment})

    if type_of_payment == 'paypal':
        await call.message.answer(await _('Введите сумму вашего пожертвования в долларах', call.message.chat.id))

    if type_of_payment == 'yoomoney':
        await call.message.answer(await _('Введите сумму вашего пожертвования в рублях', call.message.chat.id))


@router.message(UserPay.enter_amount, F.text)
async def get_user_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        return await message.answer(await _('Введите сумму в цифрах', message.chat.id))

    data = await state.get_data()

    amount_to_pay = await _('Сумма к оплате:', message.chat.id)
    service_to_pay = await _('Сервис оплаты:', message.chat.id)
    time_to_pay = await _('Время на оплату: 3 часа', message.chat.id)

    if data['type_of_payment'] == 'yoomoney':
        u = str(uuid.uuid4())
        p = Payment(
            message.chat.id,
            int(data['channel_id']),
            u,
            PaymentStatus.PENDING.value,
            int(time.time()),
            PaymentType.YOOMONEY
        )

        url = await YOOMONEY_CLIENT.create_payment(
            label=u,
            amount=amount,
            payment=p
        )

        await message.answer(
            f'{amount_to_pay} {amount} ₽\n{service_to_pay} YooMoney\n{time_to_pay}',
            reply_markup=(await keyboards.yoomoney_url(url, u, message.chat.id)).as_markup()
        )

    if data['type_of_payment'] == 'paypal':
        u = str(uuid.uuid4())
        p = Payment(
            message.chat.id,
            int(data['channel_id']),
            u,
            PaymentStatus.PENDING.value,
            int(time.time()),
            PaymentType.PAYPAL
        )

        url = await PAYPAL_CLIENT.create_payment(
            amount=amount,
            payment=p
        )

        await message.answer(
            f'{amount_to_pay} {amount} $\n{service_to_pay} PayPal\n{time_to_pay}',
            reply_markup=(await keyboards.yoomoney_url(url, u, message.chat.id)).as_markup()
        )


@router.callback_query(F.data.startswith('ycheck'))
async def check_payment(call: CallbackQuery):
    payment_uuid = call.data.split(':')[1]
    payment = await db_api.check_payment(payment_uuid)

    if payment.status == PaymentStatus.PENDING.value:
        return await call.message.answer(await _('Ожидаем оплату.', call.message.chat.id))

    if payment.status == PaymentStatus.CANCELLED.value:
        return await call.message.answer(await _('Заявка отклонена', call.message.chat.id))

    if payment.status == PaymentStatus.COMPLETED.value:
        return await call.message.answer(await _('Вы успешно оплатили заявку.', call.message.chat.id))


@router.callback_query(F.data.startswith('lang_choice'))
async def change(call: CallbackQuery):
    await db_api.update_language(call.message.chat.id, call.data.split(':')[1])
    await call.message.delete()
    await hi_admin(call.message)


@router.callback_query(F.data == 'update_language')
async def update_language(call: CallbackQuery):
    await call.message.edit_text('Choice your language', reply_markup=keyboards.language.as_markup())
