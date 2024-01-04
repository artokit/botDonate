import time
from typing import Optional
import aiosqlite
import asyncio
from config import TIME_PAYMENT_EXPIRED
from database.db_models import Channel, Wallets, Payment, PaymentType, PaymentStatus, User, InviteCode, PrUser
import os
connect: Optional[aiosqlite.Connection] = None
cursor: Optional[aiosqlite.Cursor] = None
CACHED_LANG_USERS = {}


async def _init_db():
    global connect, cursor
    connect = await aiosqlite.connect(os.path.join(os.path.dirname(__file__), 'db.sqlite'))
    cursor = await connect.cursor()


async def get_all_prs():
    await cursor.execute('SELECT * FROM prs_users')
    return await cursor.fetchall()


async def add_user(user_id: int, username: Optional[str], pr_code: Optional[str]):
    try:
        await cursor.execute('INSERT INTO USERS VALUES(?, ?, null, ?, 0)', (user_id, username, pr_code))
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


async def clear_all_payments(user_id: int):
    await cursor.execute(
        'UPDATE payments SET status = "CANCELLED" WHERE user_id = ? AND status = "PENDING"',
        (user_id, )
    )
    await connect.commit()


async def get_pr_id_by_code(code: str):
    res = await cursor.execute("SELECT * FROM invite_codes where code = ?", (code, ))
    return (await res.fetchone())[0]


async def delete_payment(payment_uuid: str):
    await cursor.execute('DELETE FROM payments WHERE payment_uuid = ?', (payment_uuid,))
    await connect.commit()


async def get_not_expired_payments(user_id: int) -> Optional[list[Payment]]:
    res = await cursor.execute(
        'SELECT * FROM PAYMENTS WHERE user_id = ? and status = "PENDING" AND time >= ?',
        (user_id, int(time.time() - TIME_PAYMENT_EXPIRED))
    )
    arr = [Payment(*i) for i in await res.fetchall()]
    return arr if arr else None


async def add_prs(user_id: int, percent: float) -> bool:
    try:
        await cursor.execute('INSERT INTO prs_users VALUES(?, ?)', (user_id, percent))
        await connect.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def check_prs(user_id: int):
    res = await cursor.execute('SELECT * FROM PRS_USERS WHERE user_id = ?', (user_id, ))
    return bool(await res.fetchall())


async def add_pr_code(pr_id: int, code: str):
    await cursor.execute('INSERT INTO invite_codes values(?, ?, null)', (pr_id, code))
    await connect.commit()


async def get_codes_by_pr_id(pr_id: int) -> list[InviteCode]:
    res = await cursor.execute('SELECT * FROM invite_codes WHERE pr_id = ?', (pr_id, ))
    return [InviteCode(*i) for i in await res.fetchall()]


async def get_count_refs_by_code(code: str) -> int:
    res = await cursor.execute('SELECT * FROM users where pr_code = ?', (code, ))
    return len([i for i in await res.fetchall()])


async def get_pr_percent_by_pr_id(pr_id: int):
    await cursor.execute('SELECT * FROM prs_users where user_id = ?', (pr_id, ))
    return (await cursor.fetchone())[1]


async def get_pr(pr_id: int) -> Optional[PrUser]:
    res = await cursor.execute("SELECT * FROM prs_users where user_id = ?", (pr_id, ))

    try:
        return PrUser(*await res.fetchone())
    except TypeError:
        pass


async def delete_pr(pr_id: int):
    await cursor.execute("DELETE FROM prs_users where user_id = ?", (pr_id, ))
    await connect.commit()


async def update_percent(user_id: int, percent: float):
    await cursor.execute("UPDATE prs_users SET percent = ? where user_id = ?", (percent, user_id))
    await connect.commit()


async def change_code_name(code: str, code_name: str):
    await cursor.execute("UPDATE invite_codes SET name_of_code = ? where code = ?", (code_name, code))
    await connect.commit()


async def update_balance(user_id: int, balance: float):
    await cursor.execute("UPDATE users SET balance = ? where user_id = ?", (balance, user_id))
    await connect.commit()


async def get_user_admin_by_channel_id(channel_id: int) -> User:
    res = await cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id, ))
    return await get_user((await res.fetchone())[0])


loop = asyncio.new_event_loop()
tasks = asyncio.wait([loop.create_task(_init_db())])
loop.run_until_complete(tasks)
