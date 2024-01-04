from dataclasses import dataclass
from typing import List
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, Video, PhotoSize
from aiogram.types import ReplyKeyboardRemove
import keyboards
from database import db_api
from translate_texts.translate import translate_text as _

router = Router()


class ChangeWallet(StatesGroup):
    enter_wallet = State()


class ChangeChannelSettings(StatesGroup):
    enter_channel_name = State()


class MakePost(StatesGroup):
    enter_button_text = State()
    enter_content = State()


class MakeNewHelloContent(StatesGroup):
    enter_content = State()


@dataclass
class Post:
    video: Video | None
    photo: List[PhotoSize] | None
    caption: str | None
    button_text: str | None
    text: str | None


async def hi_admin(message: Message):
    await message.answer(
        await _('✋Приветствую!✋\nЧто соизволите сделать?\n📋Вот список возможностей:📋', message.chat.id),
        reply_markup=await keyboards.get_admins(message.chat.id)
    )


@router.callback_query(F.data.startswith('check_channels'))
async def check_channels(call: CallbackQuery):
    channels = await db_api.get_channels_by_user(call.message.chat.id)

    if not channels:
        return await call.message.edit_text(
            await _('😥У вас нету привязанных каналов😥', call.message.chat.id),
            reply_markup=await keyboards.get_back_to_main_menu(call.message.chat.id)
        )

    page = int(call.data.split(':')[-1])
    try:
        await call.message.edit_text(
            await _('📺 Доступные вам каналы:', call.message.chat.id),
            reply_markup=(await keyboards.channels_page_generator(page, channels, call.message.chat.id)).as_markup()
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == 'back')
async def back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await hi_admin(call.message)


@router.message(F.text == '🔙Назад')
async def back_message(message: Message):
    msg = await message.answer('...', reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await hi_admin(message)


@router.callback_query(F.data == 'add_new_channel')
async def add_new_channel(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        await _('📥Отправьте новый канал📥', call.message.chat.id),
        reply_markup=await keyboards.get_shared_buttons(call.message.chat.id)
    )


@router.message(F.chat_shared)
async def on_user_shared(message: Message):
    try:
        await message.bot.get_chat(message.chat_shared.chat_id)
    except TelegramBadRequest:
        return await message.answer(
            await _('☹Бота нету в чате!☹\nПожалуйста, добавьте бота в чат и выдайте ему права администратора для работы', message.chat.id)
        )

    t = await _("Чат", message.chat.id)
    res = await db_api.add_new_channel(
        message.chat.id,
        message.chat_shared.chat_id,
        f'{t} №{abs(message.chat_shared.chat_id)}'
    )

    if res:
        await message.answer(
            await _('😄Чат был успешно добавлен в базу данных.😄', message.chat.id),
            reply_markup=ReplyKeyboardRemove()
        )
        return await hi_admin(message)

    await message.answer(await _('😄Данный канал уже есть в базе данных.😄', message.chat.id))


@router.callback_query(F.data.startswith('channel_info'))
async def get_channel_info(call: CallbackQuery, state: FSMContext):
    await state.clear()
    channel_id, page = list(map(int, call.data.split(':')[1:]))
    await state.set_data({'page': page})
    bot = await call.message.bot.get_me()
    t = await _("Ссылка для доната", call.message.chat.id)
    await call.message.edit_text(
        f'{t}: https://t.me/{bot.username}?start={channel_id}',
        reply_markup=(await keyboards.edit_channel(page, channel_id, call.message.chat.id)).as_markup()
    )


@router.callback_query(F.data == 'change_wallets')
async def select_wallet_to_change(call: CallbackQuery):
    wallets = await db_api.get_wallets(call.message.chat.id)
    text = await wallets.get_wallets_in_text(call.message.chat.id)
    await call.message.edit_text(text, reply_markup=await keyboards.get_wallets(call.message.chat.id))


@router.callback_query(F.data.startswith('wallet'))
async def change_selected_wallet(call: CallbackQuery, state: FSMContext):
    wallet_name = call.data.split(':')[1]

    await state.set_state(ChangeWallet.enter_wallet)
    await state.set_data({'wallet_name': wallet_name})
    t = await _('👨‍💻Введите счёт для', call.message.chat.id)
    await call.message.edit_text(
        f'{t} {wallet_name}',
        reply_markup=await keyboards.get_back_to_main_menu(call.message.chat.id)
    )


@router.message(ChangeWallet.enter_wallet, F.text)
async def check_new_wallet(message: Message, state: FSMContext):
    wallet_name = (await state.get_data())['wallet_name']
    await db_api.change_wallet(message.chat.id, message.text, wallet_name)
    t = await _('Изменения сохранены! Текущий кошелёк:', message.chat.id)
    await message.answer(f'{t} {wallet_name}', reply_markup=await keyboards.get_admins(message.chat.id))


@router.callback_query(F.data.startswith('change_channel_name'))
async def change_channel_name(call: CallbackQuery, state: FSMContext):
    await state.set_state(ChangeChannelSettings.enter_channel_name)
    await state.set_data({'channel_id': call.data.split(':')[1]})
    await call.message.edit_text(
        await _('👨‍💻Введите новое название канала', call.message.chat.id),
        reply_markup=await keyboards.get_back_to_main_menu(call.message.chat.id)
    )


@router.message(ChangeChannelSettings.enter_channel_name, F.text)
async def save_new_channel_name(message: Message, state: FSMContext):
    channel_id = (await state.get_data())['channel_id']
    await db_api.update_channel_name(channel_id, message.text)
    await message.answer(
        await _('Название канала было изменено!', message.chat.id),
        reply_markup=await keyboards.get_admins(message.chat.id)
    )


@router.callback_query(F.data.startswith('post'))
async def make_new_post(call: CallbackQuery, state: FSMContext):
    channel_id = int(call.data.split(':')[1])
    page = (await state.get_data()).get('page', 1)
    await state.set_state(MakePost.enter_button_text)
    await state.update_data({'channel_id': channel_id})
    await call.message.edit_text(
        await _('Введите текст кнопки с ссылкой на донат', call.message.chat.id),
        reply_markup=(await keyboards.go_back_channel(page, channel_id, call.message.chat.id)).as_markup()
    )


@router.message(MakePost.enter_button_text, F.text)
async def get_post_text(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get('channel_id')
    page = data.get('page', 1)
    post = Post(None, None, None, message.text, None)
    await state.set_state(MakePost.enter_content)
    await state.update_data({'post': post})
    await message.answer(
        await _('Отправьте фото/видео и текст одним сообщением (максимум 1 фото/видео)', message.chat.id),
        reply_markup=(await keyboards.go_back_channel(page, channel_id, message.chat.id)).as_markup()
    )


@router.message(MakePost.enter_content, F.photo)
@router.message(MakePost.enter_content, F.video)
@router.message(MakePost.enter_content, F.text)
async def ready_post(message: Message, state: FSMContext):
    data = await state.get_data()

    post: Post = data.get('post')
    post.video = message.video
    post.photo = message.photo
    post.caption = message.md_text
    post.text = message.md_text

    await send_post(post, message.chat.id, message.bot, data.get('channel_id'))
    await message.answer(
        await _('Вы хотите сделать пост ?', message.chat.id),
        reply_markup=keyboards.agree.as_markup()
    )


@router.callback_query(F.data == 'disagree_post')
async def disagree_post(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(await _('❌ Действие отменено ❌', call.message.chat.id))
    await hi_admin(call.message)


@router.callback_query(F.data == 'agree_post')
async def agree_post(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get('channel_id')
    post = data.get('post')

    try:
        await send_post(post, channel_id, call.message.bot, data.get('channel_id'))
        await call.message.edit_text(await _('Пост был создан в канале!', call.message.chat.id))

    except TelegramBadRequest:
        await call.message.answer(await _("Ошибка!\nУ бота нету прав на отправку сообщений в данном канале.", call.message.chat.id))

    except TelegramForbiddenError:
        await call.message.answer(await _("Ошибка!\nБота нету в канале", call.message.chat.id))

    await state.clear()
    await hi_admin(call.message)


@router.callback_query(F.data.startswith('change_hello_msg'))
async def change_hello_msg(call: CallbackQuery, state: FSMContext):
    channel_id = int(call.data.split(':')[1])
    await state.set_state(MakeNewHelloContent.enter_content)
    await state.set_data({'channel_id': channel_id})

    await call.message.edit_text(
        await _('Введите новое сообщение которое будет видеть человек при старте бота.', call.message.chat.id)
    )


@router.message(MakeNewHelloContent.enter_content, F.text)
@router.message(MakeNewHelloContent.enter_content, F.photo)
@router.message(MakeNewHelloContent.enter_content, F.video)
async def new_hello_text(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data['channel_id']

    if message.photo:
        await db_api.update_hello_message(photo=message.photo[-1].file_id, channel_id=channel_id, text=message.md_text)

    if message.video:
        await db_api.update_hello_message(video=message.video.file_id, channel_id=channel_id, text=message.md_text)

    if not (message.video or message.photo):
        await db_api.update_hello_message(text=message.md_text, channel_id=channel_id)

    await state.clear()
    await message.answer(await _('Приветственное сообщение было изменено!', message.chat.id))
    await hi_admin(message)


async def send_post(post: Post, chat_id: int, bot: Bot, channel_id: int):
    # chat_id - куда будет отправляться сообщение.
    # channel_id - на какой канал будут приходить донаты.

    keyboard = keyboards.get_button_post(channel_id, post.button_text, (await bot.get_me()).username).as_markup()
    if post.video:
        return await bot.send_video(
            chat_id,
            video=post.video.file_id,
            caption=post.caption,
            reply_markup=keyboard,
            parse_mode='markdownv2'
        )

    if post.photo:
        return await bot.send_photo(
            chat_id,
            photo=post.photo[-1].file_id,
            caption=post.caption,
            reply_markup=keyboard,
            parse_mode='markdownv2'
        )

    await bot.send_message(
        chat_id,
        text=post.text,
        reply_markup=keyboard,
        parse_mode='markdownv2'
    )
