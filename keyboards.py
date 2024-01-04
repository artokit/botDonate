import math
from typing import Optional
from aiogram.types import KeyboardButtonRequestChat, KeyboardButtonRequestUser
from aiogram.utils.keyboard import (InlineKeyboardBuilder, InlineKeyboardButton, ReplyKeyboardBuilder, KeyboardButton,
                                    InlineKeyboardMarkup, ReplyKeyboardMarkup)
from config import ADMINS
from database import db_api
from database.db_models import Channel, InviteCode
from payments.cryptomus.cryptomus_api import ALLOWED_CRYPTOCURRENCIES
from translate_texts.translate import translate_text as _


async def get_admins(user_id: int) -> InlineKeyboardMarkup:
    admins = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(text=await _('📕Посмотреть доступные каналы📕', user_id),
                             callback_data='check_channels:1'),
        # InlineKeyboardButton(text=await _('💵Изменить реквизиты💵', user_id),
        #                      callback_data='change_wallets'),
        InlineKeyboardButton(text=await _('📥Добавить новый канал📥', user_id),
                             callback_data='add_new_channel'),
        InlineKeyboardButton(text=await _('🌇Изменить язык🌇', user_id),
                             callback_data='update_language'),
        InlineKeyboardButton(
            text=await _("💰Финансы💰", user_id),
            callback_data='finances'
        )
    ]

    if user_id in ADMINS:
        buttons.append(
            InlineKeyboardButton(
                text=await _("➕Управление пиарщиками➕", user_id),
                callback_data='manage_pr'
            )
        )
    if await db_api.check_prs(user_id):
        buttons.append(InlineKeyboardButton(
            text=await _('Кабинет пиарщика', user_id),
            callback_data='cabinet_of_prs')
        )

    admins.row(
        *buttons,
        width=1
    )
    return admins.as_markup()


async def manage_prs(user_id: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=await _("➕Добавить нового пиарщика➕", user_id),
            callback_data='add_new_pr'
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=await _("Получить всех пиарщиков", user_id),
            callback_data='get_all_prs'
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=await _("Изменить процент пиарщика", user_id),
            callback_data='change_pr_id'
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=await _("Удалить пиарщика", user_id),
            callback_data='del_pr'
        )
    )
    back_text = await _('Назад', user_id)
    keyboard.row(InlineKeyboardButton(text=f"⬅️ {back_text}", callback_data='back'))
    return keyboard.as_markup()


async def get_back_to_main_menu(user_id: int) -> InlineKeyboardMarkup:
    back_to_main_menu = InlineKeyboardBuilder()
    back_text = await _('Назад', user_id)
    back_to_main_menu.add(InlineKeyboardButton(text=f"⬅️ {back_text}", callback_data='back'))
    return back_to_main_menu.as_markup()


async def get_shared_buttons(user_id: int) -> ReplyKeyboardMarkup:
    shared_buttons = ReplyKeyboardBuilder()
    shared_buttons.row(
        KeyboardButton(
            text=await _("✉Отправить канал✉", user_id),
            request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=True, bot_is_member=False)
        ),
        KeyboardButton(
            text=await _("✉Отправить группу✉", user_id),
            request_chat=KeyboardButtonRequestChat(request_id=1, chat_is_channel=False, bot_is_member=False)
        ),
        KeyboardButton(text=await _("🔙Назад", user_id)),
        width=1
    )
    return shared_buttons.as_markup(resize_keyboard=True)


async def get_wallets(user_id: int) -> InlineKeyboardMarkup:
    wallets = InlineKeyboardBuilder()
    wallets.row(InlineKeyboardButton(text="YooMoney", callback_data='wallet:yoomoney'))
    wallets.row(InlineKeyboardButton(text="PayPal", callback_data='wallet:paypal'))
    wallets.row(InlineKeyboardButton(text="Crypto", callback_data='wallet:crypto'))
    wallets.row(InlineKeyboardButton(text=await _("⬅️ Назад", user_id),
                                     callback_data='back'))
    return wallets.as_markup()


agree = InlineKeyboardBuilder()
agree.row(InlineKeyboardButton(text="✅", callback_data='agree_post'))
agree.row(InlineKeyboardButton(text="❌", callback_data="disagree_post"))

language = InlineKeyboardBuilder()
language.row(
    InlineKeyboardButton(text='🇷🇺 Русский 🇷🇺', callback_data='lang_choice:rus'),
    InlineKeyboardButton(text='🇬🇧 English 🇬🇧', callback_data='lang_choice:eng'),
    InlineKeyboardButton(text='🇪🇸 Español 🇪🇸', callback_data='lang_choice:sp'),
    InlineKeyboardButton(text='🇨🇳 西班牙語 🇨🇳', callback_data='lang_choice:ch'),
    width=1
)


async def channels_page_generator(page: int, channels: list[Channel], user_id: int) -> Optional[InlineKeyboardBuilder]:
    channels_per_page_count = 5
    max_page = math.ceil(len(channels) / channels_per_page_count)

    if page > max_page:
        page = 1

    if page == 0:
        page = max_page

    keyboard = InlineKeyboardBuilder()
    start = (page - 1) * channels_per_page_count
    end = page * channels_per_page_count

    for channel in channels[start:end]:
        keyboard.row(InlineKeyboardButton(
            text=f'💬 {channel.channel_name} 💬',
            callback_data=f'channel_info:{channel.channel_id}:{page}')
        )

    keyboard.row(
        InlineKeyboardButton(text="⬅", callback_data=f'check_channels:{page - 1}'),
        InlineKeyboardButton(text=f"{page}/{max_page}", callback_data="none"),
        InlineKeyboardButton(text="➡", callback_data=f'check_channels:{page + 1}'),
    )
    back = await _('⬅ Назад', user_id)
    keyboard.row(InlineKeyboardButton(text=back, callback_data='back'))

    return keyboard


async def edit_channel(page: int, channel_id: int, user_id: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=await _("✏Изменить название✏", user_id),
                             callback_data=f"change_channel_name:{channel_id}"),
        InlineKeyboardButton(text=await _("📩Изменить приветственное сообщение📩", user_id),
                             callback_data=f"change_hello_msg:{channel_id}"),
        InlineKeyboardButton(text=await _("📫Сделать пост с кнопкой📫", user_id),
                             callback_data=f"post:{channel_id}"),
        InlineKeyboardButton(text=await _('⬅️ Назад', user_id),
                             callback_data=f'check_channels:{page}'),
        width=1
    )
    return keyboard


async def go_back_channel(page: int, channel_id: int, user_id: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text=await _(f'⬅️ Назад', user_id),
        callback_data=f'channel_info:{channel_id}:{page}')
    )
    return keyboard


def get_button_post(channel_id: int, button_text: str, bot_username: str):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=button_text, url=f'https://t.me/{bot_username}?start={channel_id}'))
    return keyboard


def get_currencies() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    for i in ALLOWED_CRYPTOCURRENCIES:
        keyboard.row(InlineKeyboardButton(text=i, callback_data=f'choice_currency:{i}'))

    return keyboard.as_markup()


async def get_transfer_keyboard(user_id: int, channel_id: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text='💵YooMoney💵',
        callback_data=f'pay:yoomoney:{channel_id}'
    ), width=1)
    keyboard.row(InlineKeyboardButton(text='💵Paypal💵', callback_data=f'pay:paypal:{channel_id}'), width=1)
    keyboard.row(InlineKeyboardButton(
        text=await _('💵Криптовалюта💵', user_id),
        callback_data=f'pay:crypto:{channel_id}'),
        width=1
    )
    return keyboard


async def pay_url(url: str, user_id: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=await _("💰Оплата💰", user_id), url=url))
    return keyboard


async def paypal_keyboard(url: str, user_id: int, payment_uuid: str):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=await _("💰Оплата💰", user_id), url=url))
    # keyboard.row(
    #     InlineKeyboardButton(
    #         text=await _("Проверить платёж", user_id),
    #         callback_data=f'check_paypal:{payment_uuid}'
    #     )
    # )
    return keyboard.as_markup()


async def invite_user(user_id: int):
    keyboard = ReplyKeyboardBuilder()
    keyboard.row(KeyboardButton(
        text=await _('Отправить пользователя', user_id),
        request_user=KeyboardButtonRequestUser(request_id=3)),
    )
    return keyboard.as_markup(resize_keyboard=True)


async def get_prs_keyboard(user_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(
        text=await _('Посмотреть мои рекламные ссылки', user_id),
        callback_data='check_urls')
    )
    keyboard.row(InlineKeyboardButton(
        text=await _('Создать рекламную ссылку', user_id),
        callback_data='create_url')
    )
    back_text = await _('Назад', user_id)
    keyboard.row(InlineKeyboardButton(text=f"⬅️ {back_text}", callback_data='back'))
    return keyboard.as_markup()


async def pr_links_info(invites: list[InviteCode]):
    keyboard = InlineKeyboardBuilder()
    for invite in invites:
        keyboard.row(
            InlineKeyboardButton(
                text=invite.name_of_code if invite.name_of_code else invite.code,
                callback_data=f'info_code:{invite.code}'
            )
        )

    back_text = await _('Назад', invites[0].pr_id)
    keyboard.row(InlineKeyboardButton(text=f"⬅️ {back_text}", callback_data='back'))
    return keyboard.as_markup()


async def info_url_keyboard(code: str, user_id: int):
    keyboard = InlineKeyboardBuilder()
    change_name_code = await _("Изменить название кода", user_id)
    keyboard.row(InlineKeyboardButton(text=change_name_code, callback_data=f"change_name_code:{code}"))
    back_text = await _('Назад', user_id)
    keyboard.row(InlineKeyboardButton(text=f"⬅️ {back_text}", callback_data='check_urls'))
    return keyboard.as_markup()


async def request_pay(user_id: int):
    keyboard = InlineKeyboardBuilder()
    yoomoney = await _("Вывод YooMoney", user_id)
    crypto = await _("Вывод Cryptomus", user_id)
    keyboard.row(InlineKeyboardButton(text=yoomoney, callback_data="salary:yoomoney"))
    keyboard.row(InlineKeyboardButton(text=crypto, callback_data="salary:crypto"))
    return keyboard.as_markup()
