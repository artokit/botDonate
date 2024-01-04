import time
import uuid
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils import markdown
from database import db_api
import keyboards
from config import SUPPORT_TG, COURSE_USD
from database.db_models import Payment, PaymentStatus, PaymentType
from routers.admins import hi_admin
from aiogram import F
from payments.payment_manager import YOOMONEY_CLIENT, PAYPAL_CLIENT, CRYPTOMUS_CLIENT
from translate_texts.translate import translate_text as _


class UserPay(StatesGroup):
    enter_amount = State()
    select_currency = State()


class PayOfBalance(StatesGroup):
    enter_wallet = State()
    enter_sum = State()


router = Router()


@router.message(Command('start'))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await db_api.add_user(message.chat.id, message.from_user.username, get_pr_code(message.text))
    user = await db_api.get_user(message.chat.id)

    if message.text == '/start' or message.text.startswith('/start pr_'):
        if not user.lang:
            return await message.answer('Choice your language', reply_markup=keyboards.language.as_markup())

        return await hi_admin(message)

    await donate(message)


def get_pr_code(text: str):
    if text.startswith('/start pr_'):
        return text.replace('/start pr_', '')


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

    not_expired_payments = await db_api.get_not_expired_payments(call.message.chat.id)
    if not_expired_payments:
        return await call.message.answer(
            await _('У вас уже есть недавно созданная заявка. Подождите немного перед созданием новой', call.message.chat.id)
        )

    await state.set_state(UserPay.enter_amount)
    await state.set_data({'channel_id': channel_id, 'type_of_payment': type_of_payment})

    if type_of_payment == 'paypal':
        await call.message.answer(await _('Введите сумму вашего пожертвования в долларах', call.message.chat.id))

    if type_of_payment == 'yoomoney':
        await call.message.answer(await _('Введите сумму вашего пожертвования в рублях (минимум 1 рубль)', call.message.chat.id))

    if type_of_payment == 'crypto':
        await state.set_state(UserPay.select_currency)
        await call.message.answer(
            await _('Выберите криптовалюту', call.message.chat.id),
            reply_markup=keyboards.get_currencies()
        )


@router.message(UserPay.enter_amount, F.text)
async def get_user_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        return await message.answer(await _('Введите сумму в цифрах', message.chat.id))

    data = await state.get_data()

    await db_api.clear_all_payments(message.chat.id)

    amount_to_pay = await _('Сумма к оплате:', message.chat.id)
    service_to_pay = await _('Сервис оплаты:', message.chat.id)
    time_to_pay = await _('Система автоматически засчитает ваш платёж и отправит сообщение об этом',
                          message.chat.id)

    support_text = await _('При возникновении ошибок пишите нам', message.chat.id)

    if data['type_of_payment'] == 'yoomoney':
        if amount < 1:
            return await message.answer(await _('Ошибка! Введите сумму большую одного рубля снова', message.chat.id))
        p = Payment.new_payment(
            message.chat.id,
            int(data['channel_id']),
            PaymentType.YOOMONEY
        )

        url = await YOOMONEY_CLIENT.create_payment(
            label=p.payment_uuid,
            amount=amount,
            payment=p
        )

        await answer_uuid_payment(message, p.payment_uuid)
        await message.answer(
            f'{amount_to_pay} {amount} ₽\n{service_to_pay} YooMoney\n{time_to_pay}\n{support_text}: {SUPPORT_TG}\n',
            reply_markup=(await keyboards.pay_url(url, message.chat.id)).as_markup(),
        )
        await state.clear()

    if data['type_of_payment'] == 'paypal':

        url = await PAYPAL_CLIENT.create_payment(
            amount=amount,
        )
        if not url:
            return await message.answer(await _("Произошла ошибка. Возможно вы ввели неправильную сумму пожертвования.\nПопробуйте снова", message.chat.id))
        token = url.split('token=')[1]

        p = Payment(
            message.chat.id,
            int(data['channel_id']),
            token,
            PaymentStatus.PENDING.value,
            int(time.time()),
            PaymentType.PAYPAL
        )
        await db_api.add_payment(p)
        await message.answer(
            f'{amount_to_pay} {amount} $\n{service_to_pay} PayPal\n{time_to_pay}',
            reply_markup=await keyboards.paypal_keyboard(url, message.chat.id, p.payment_uuid)
        )

    if data['type_of_payment'] == 'crypto':
        data = await state.get_data()
        p = Payment.new_payment(
            message.chat.id,
            int(data['channel_id']),
            PaymentType.CRYPTO
        )
        res = await CRYPTOMUS_CLIENT.create_payment(payment=p, amount=amount, to_currency=data['currency'])
        if not res['state']:
            await answer_uuid_payment(message, p.payment_uuid)
            await message.answer(
                f'{amount_to_pay} {amount} $\n{service_to_pay} Cryptomus\n{time_to_pay}\n{support_text}: {SUPPORT_TG}\n',
                reply_markup=(await keyboards.pay_url(res['result']['url'], message.chat.id)).as_markup(),
            )
            return await state.clear()

        await db_api.delete_payment(p.payment_uuid)
        text = res.get('message') or res.get('errors')

        if isinstance(text, dict):
            text = '\n'.join([text[i][0] for i in text])

        error = markdown.text(await _('Ошибка!\nСообщение от платёжной системы', message.chat.id))
        try_again = await _('Попробуйте снова', message.chat.id)
        await message.answer(
            f'{error}:\n***{text}***\n\n{try_again}:',
            parse_mode='markdown',
            reply_markup=(await keyboards.get_transfer_keyboard(message.chat.id, data['channel_id'])).as_markup()
        )
        await state.clear()


async def answer_uuid_payment(message: Message, payment_uuid: str):
    id_text = await _('Уникальный идентификатор заявки', message.chat.id)
    await message.answer(f'{id_text}: `{payment_uuid}`\n\n⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️⬇️', parse_mode='markdownv2')


@router.callback_query(F.data.startswith('check_paypal'))
async def check_paypal(call: CallbackQuery):
    payment_uuid = call.data.split(':')[1]
    PAYPAL_CLIENT.check_payment(payment_uuid)


@router.callback_query(F.data.startswith('choice_currency'))
async def choice_currency(call: CallbackQuery, state: FSMContext):
    currency = call.data.split(':')[1]
    await state.set_state(UserPay.enter_amount)
    await state.update_data({'currency': currency})
    choice_crypto = await _('Выбранная криптовалюта', call.message.chat.id)
    enter_amount = markdown.text(await _('Введите количество (вводить сумму в долларах)', call.message.chat.id))
    await call.message.edit_text(f'{choice_crypto}: ***{currency}***\n{enter_amount}:', parse_mode='markdown')


@router.callback_query(F.data.startswith('lang_choice'))
async def change(call: CallbackQuery):
    await db_api.update_language(call.message.chat.id, call.data.split(':')[1])
    await call.message.delete()
    await hi_admin(call.message)


@router.callback_query(F.data == 'update_language')
async def update_language(call: CallbackQuery):
    await call.message.edit_text('Choice your language', reply_markup=keyboards.language.as_markup())


@router.callback_query(F.data == 'finances')
async def get_finance(call: CallbackQuery):
    user = await db_api.get_user(call.message.chat.id)
    t = await _('Ваш текущий баланс', call.message.chat.id)
    await call.message.answer(
        f"{t}: {round(user.balance, 4)}$",
        reply_markup=await keyboards.request_pay(call.message.chat.id)
    )


@router.callback_query(F.data == 'salary:yoomoney')
async def pay_to(call: CallbackQuery, state: FSMContext):
    await state.set_state(PayOfBalance.enter_wallet)
    await call.message.answer(
        await _("Введите свой кошелёк", call.message.chat.id),
        reply_markup=await keyboards.get_back_to_main_menu(call.message.chat.id)
    )


# @router.callback_query(F.data == 'pay_of_to:crypto')
# async def pay_of_to()


@router.message(PayOfBalance.enter_wallet, F.text)
async def pay_of(message: Message, state: FSMContext):
    wallet = message.text
    await state.set_state(PayOfBalance.enter_sum)
    await state.update_data({'wallet': wallet})
    await message.answer('Введите сумму на вывод в рублях')


@router.message(PayOfBalance.enter_sum, F.text)
async def pay_sum(message: Message, state: FSMContext):
    data = await state.get_data()
    wallet = data['wallet']
    amount = int(message.text)

    if amount <= 0:
        return await message.answer(await _('Введите число болшее нуля', message.chat.id))

    user = await db_api.get_user(message.chat.id)
    if user.balance*COURSE_USD < amount:
        return await message.answer(await _('Введите сумму не превышающую ваш баланс', message.chat.id))

    try:
        await YOOMONEY_CLIENT.pay_of_to(wallet, amount)
        await db_api.update_balance(user.user_id, round(user.balance-(amount/COURSE_USD), 4))
        await message.answer(await _('Вывод был совершён успешно!', message.chat.id), reply_markup=await keyboards.get_admins(message.chat.id))
        await state.clear()
    except:
        await message.answer(await _("Не удалось вывести деньги.\nВозможно, вы указали слишком маленькую сумму или неправильо ввели кошелёк", message.chat.id), reply_markup=await keyboards.get_admins(message.chat.id))
        await state.clear()
