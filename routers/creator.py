import asyncio
import os

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, FSInputFile
import keyboards
from database import db_api
from aiogram.types import ReplyKeyboardRemove
from routers.admins import hi_admin
from translate_texts.translate import translate_text as _

router = Router()


class AddUser(StatesGroup):
    enter_user_id = State()
    enter_percent = State()


class ChangePercentPr(StatesGroup):
    enter_user_id = State()
    enter_new_percent = State()


class DeletePr(StatesGroup):
    enter_id = State()


@router.callback_query(F.data == 'manage_pr')
async def manage_pr(call: CallbackQuery):
    await call.message.edit_text(
        await _("Выберите действие", call.message.chat.id),
        reply_markup=await keyboards.manage_prs(call.message.chat.id)
    )


@router.callback_query(F.data == 'get_all_prs')
async def get_all_prs(call: CallbackQuery):
    await call.message.delete()
    prs = await db_api.get_all_prs()
    f = open('prs.txt', 'w')
    for pr in prs:
        f.write(f'{pr[0]} {pr[1]}%\n')

    f.close()

    await call.message.answer_document(
        FSInputFile("prs.txt"),
        caption=await _("Файл с данными о пиарщиках", call.message.chat.id)
    )
    os.remove('prs.txt')

    await call.message.answer(
        await _("Что будем делать дальше?", call.message.chat.id),
        reply_markup=await keyboards.get_admins(call.message.chat.id)
    )


@router.callback_query(F.data == 'change_pr_id')
async def change_pr_id(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        await _("Введите id пиарщика", call.message.chat.id),
        reply_markup=await keyboards.get_back_to_main_menu(call.message.chat.id)
    )
    await state.set_state(ChangePercentPr.enter_user_id)


@router.callback_query(F.data == 'del_pr')
async def del_pr(call: CallbackQuery, state: FSMContext):
    await state.set_state(DeletePr.enter_id)
    await call.message.answer(await _("Введите айди пиарщика", call.message.chat.id))


@router.message(DeletePr.enter_id, F.text)
async def get_id_pr_for_delete(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer(
            await _("Введите ID", message.chat.id),
            reply_markup=await keyboards.get_back_to_main_menu(message.chat.id)
        )

    await state.clear()
    pr_user = await db_api.get_pr(int(message.text))

    if not pr_user:
        return await message.answer(
            await _("Такого человека и не было в БД :(", message.chat.id),
            reply_markup=await keyboards.get_admins(message.chat.id)
        )

    await db_api.delete_pr(int(message.text))
    await message.answer(
        await _("Пиарщик был удалён успешно!", message.chat.id),
        reply_markup=await keyboards.get_admins(message.chat.id)
    )


@router.message(ChangePercentPr.enter_user_id, F.text)
async def get_pr_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer(await _("Введите ID", message.chat.id))

    if not await db_api.get_pr(int(message.text)):
        return await message.answer(await _("Такого пиарщика нету в БД", message.chat.id))

    await state.update_data({'user_id': int(message.text)})
    await state.set_state(ChangePercentPr.enter_new_percent)
    await message.answer(
        await _("Какой хотите поставить процент пиарщику ?", message.chat.id),
        reply_markup=await keyboards.get_back_to_main_menu(message.chat.id)
    )


@router.message(ChangePercentPr.enter_new_percent, F.text)
async def get_new_percent(message: Message, state: FSMContext):
    try:
        percent = float(message.text.replace(',', '.'))
    except TypeError:
        return await message.answer(await _("Введите процент числом", message.chat.id))

    data = await state.get_data()
    user_id = data['user_id']
    await db_api.update_percent(user_id, percent)
    await state.clear()

    await message.answer(
        await _("Процент у пиарщика был изменён", message.chat.id),
        reply_markup=await keyboards.get_admins(message.chat.id)
    )


@router.callback_query(F.data == 'add_new_pr')
async def add_new_pr(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddUser.enter_user_id)
    await call.message.answer(
        await _("Введите ID пиарщика или отправьте его контакт", call.message.chat.id),
        reply_markup=await keyboards.invite_user(call.message.chat.id)
    )


@router.message(AddUser.enter_user_id, F.text)
async def enter_user_id(message: Message, state: FSMContext):
    if message.text.isdigit():
        return await save_pr(int(message.text), state, message)

    await message.answer(await _('Введите цифры', message.chat.id))


@router.message(AddUser.enter_user_id, F.user_shared)
async def get_chat_shared(message: Message, state: FSMContext):
    await save_pr(message.user_shared.user_id, state, message)


@router.message(AddUser.enter_percent, F.text)
async def get_pr_percent(message: Message, state: FSMContext):
    try:
        percent = float(message.text.replace(',', '.'))
    except TypeError:
        return await message.answer(await _('Введите процент', message.chat.id))

    data = await state.get_data()
    await add_user_in_prs_table(data['user_id'], percent, message, state)


async def save_pr(user_id: int, state: FSMContext, message: Message):
    await state.update_data({'user_id': user_id})
    await state.set_state(AddUser.enter_percent)
    await message.answer(await _('Введите процент пиарщика:', message.chat.id), reply_markup=ReplyKeyboardRemove())


async def add_user_in_prs_table(user_id: int, percent: float, message: Message, state: FSMContext):
    res = await db_api.add_prs(user_id, percent)

    if res:
        await state.clear()
        await message.answer(
            await _('Пиарщик был успешно добавлен в БД!', message.chat.id),
            reply_markup=ReplyKeyboardRemove()
        )
        await asyncio.sleep(2)
        return await hi_admin(message)

    return await message.answer(await _("Данный пиарщик уже есть в БД", message.chat.id))
