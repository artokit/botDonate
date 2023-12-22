from typing import Optional
import aiosqlite
import asyncio
from db_models import Channel, Wallets, Payment, PaymentType, PaymentStatus, User

connect: Optional[aiosqlite.Connection] = None
cursor: Optional[aiosqlite.Cursor] = None
CACHED_LANG_USERS = {}


async def _init_db():
    global connect, cursor
    connect = await aiosqlite.connect('db.sqlite')
    cursor = await connect.cursor()


async def add_user(user_id: int, username: Optional[str]):
    try:
        await cursor.execute('INSERT INTO USERS VALUES(?, ?, null)', (user_id, username))
        await cursor.execute('INSERT INTO WALLETS VALUES(?, null, null, null)', (user_id, ))
        await connect.commit()
    except aiosqlite.IntegrityError:
        pass


async def get_user(user_id: int) -> User:
    res = await cursor.execute('SELECT * FROM USERS where user_id = ?', (user_id,))
    return User(*await res.fetchone())


async def update_language(user_id: int, lang: str):
    await cursor.execute('UPDATE USERS SET lang = ? where user_id = ?', (lang, user_id))
    await connect.commit()
    CACHED_LANG_USERS[user_id] = lang


async def get_language(user_id: int) -> Optional[str]:
    if user_id in CACHED_LANG_USERS:
        return CACHED_LANG_USERS[user_id]
    else:
        lang = (await get_user(user_id)).lang
        CACHED_LANG_USERS[user_id] = lang
        return lang


async def get_channels_by_user(user_id: int) -> list[Channel]:
    res = await cursor.execute('SELECT * FROM CHANNELS where user_id = ?', (user_id, ))
    return [Channel(*i) for i in await res.fetchall()]


async def change_wallet(user_id: int, wallet: str, wallet_name: str):
    await cursor.execute(f'UPDATE WALLETS SET {wallet_name} = ? where user_id = ?', (wallet, user_id))
    await connect.commit()


async def add_new_channel(user_id: int, channel_id: int, channel_name: str) -> bool:
    # True - канал успешно был создан.
    try:
        await cursor.execute(
            'INSERT INTO CHANNELS VALUES(?, ?, ?, ?, ?, ?)',
            (user_id, channel_id, channel_name, 'donate', None, None)
        )
        await connect.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def get_wallets(user_id: int) -> Wallets:
    res = await cursor.execute('SELECT * FROM WALLETS WHERE user_id = ?', (user_id, ))
    return Wallets(*await res.fetchone())


async def update_channel_name(channel_id: int, channel_name: str):
    await cursor.execute('UPDATE CHANNELS SET channel_name = ? where channel_id = ?', (channel_name, channel_id))
    await connect.commit()


async def get_channel_by_id(channel_id: int) -> Channel:
    res = await cursor.execute('SELECT * FROM CHANNELS WHERE channel_id = ?', (channel_id, ))
    return Channel(*await res.fetchone())


async def update_hello_message(channel_id: int, photo: Optional[str] = None, video: Optional[str] = None, text: Optional[str] = None):
    await cursor.execute(
        'UPDATE CHANNELS SET photo = ?, hello_text_content = ?, video = ? WHERE channel_id = ?',
        (photo, text, video, channel_id),
    )
    await connect.commit()


async def add_payment(payment: Payment):
    await cursor.execute(
        'INSERT INTO PAYMENTS VALUES(?, ?, ?, ?, ?, ?)',
        (payment.user_id, payment.channel_id, payment.payment_uuid, payment.status, payment.time,
         payment.payment_type.value)
    )
    await connect.commit()


async def check_payment(payment_uuid: str) -> Payment:
    res = await cursor.execute('SELECT * FROM PAYMENTS WHERE payment_uuid = ?', (payment_uuid,))
    return Payment(*await res.fetchone())


async def get_active_payments_by_type(payment_type: PaymentType) -> list[Payment]:
    res = await cursor.execute(
        'SELECT * FROM payments where type = ? AND status = ?',
        (payment_type.value, PaymentStatus.PENDING.value)
    )
    return [Payment(*i) for i in await res.fetchall()]


async def change_payment_status(payment_uuid: str, payment_status: PaymentStatus):
    await cursor.execute(
        'UPDATE payments SET status = ? WHERE payment_uuid = ?',
        (payment_status.value, payment_uuid)
    )
    await connect.commit()


async def check_user_have_any_pending_payments(user_id) -> bool:
    res = await cursor.execute(
        'SELECT * FROM payments WHERE user_id = ? and status = ?',
        (user_id, PaymentStatus.PENDING.value)
    )
    return not not await res.fetchone()


loop = asyncio.new_event_loop()
tasks = asyncio.wait([loop.create_task(_init_db())])
loop.run_until_complete(tasks)
