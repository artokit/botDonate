from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.utils import markdown
from database import db_api
from translate_texts.translate import translate_text as _
import keyboards
import random

router = Router()


class ChangeNameOfCode(StatesGroup):
    enter_name = State()


@router.callback_query(F.data == 'cabinet_of_prs')
async def get_cabinet_of_prs(call: CallbackQuery):
    await call.message.edit_text(
        await _('Выберите действие', call.message.chat.id),
        reply_markup=await keyboards.get_prs_keyboard(call.message.chat.id)
    )


@router.callback_query(F.data == 'check_urls')
async def get_urls_info(call: CallbackQuery):
    invite_codes = await db_api.get_codes_by_pr_id(call.message.chat.id)

    if invite_codes:
        return await call.message.edit_text(
            await _("Ниже представлены все ваши ссылки.", call.message.chat.id),
            reply_markup=await keyboards.pr_links_info(invite_codes)
        )

    await call.message.edit_text(
        await _("У вас пока что нету кодов", call.message.chat.id),
        reply_markup=await keyboards.get_admins(call.message.chat.id)
    )


@router.callback_query(F.data == 'create_url')
async def get_create_url(call: CallbackQuery):
    letters = 'qwertyuiopasdfghjklzxcvbnm1234567890'
    t = await _('Ваша рекламная ссылка', call.message.chat.id)
    code = "".join(random.choices(letters, k=8))

    await db_api.add_pr_code(call.message.chat.id, code)
    await call.message.answer(
        f'{t}: https://t.me/{(await call.bot.get_me()).username}?start=pr_{code}',
        reply_markup=await keyboards.get_admins(call.message.chat.id),
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith('info_code'))
async def get_info_code(call: CallbackQuery):
    code = call.data.split(':')[1]
    invited = markdown.text(await db_api.get_count_refs_by_code(code))
    percent = markdown.text(await db_api.get_pr_percent_by_pr_id(call.message.chat.id))

    info = markdown.text(await _("Информация по коду", call.message.chat.id))
    invited_by_code = markdown.text(await _("Всего приглашенно по этому коду людей", call.message.chat.id))
    your_percent = markdown.text(await _("Ваш процент", call.message.chat.id))
    your_url_invite = markdown.text(await _("*Ссылка для приглашения новых людей*", call.message.chat.id))
    url = markdown.text(f'https://t.me/{(await call.bot.get_me()).username}?start=pr_{code}')

    await call.message.edit_text(
        f"{info} ***{code}***\n\n"
        f"{invited_by_code}: ***{invited}***\n"
        f"{your_percent}: ***{percent}***%\n"
        f"{your_url_invite}: `{url}`",
        parse_mode='markdown',
        reply_markup=await keyboards.info_url_keyboard(code, call.message.chat.id)
    )


@router.callback_query(F.data.startswith('change_name_code'))
async def change_name_code(call: CallbackQuery, state: FSMContext):
    code = call.data.split(':')[1]
    await state.update_data({'code': code})
    await state.set_state(ChangeNameOfCode.enter_name)
    await call.message.answer(await _("Ведите название кода", call.message.chat.id))


@router.message(ChangeNameOfCode.enter_name, F.text)
async def get_name_of_code(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data['code']
    await db_api.change_code_name(code, message.text)
    invite_codes = await db_api.get_codes_by_pr_id(message.chat.id)
    await message.answer(
        await _("Название кода было изменено", message.chat.id),
        reply_markup=await keyboards.pr_links_info(invite_codes)
    )
    await state.clear()
