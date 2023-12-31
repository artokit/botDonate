import time
import uuid
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from translate_texts.translate import translate_text as _


@dataclass
class InviteCode:
    pr_id: int
    code: str
    name_of_code: str


@dataclass
class User:
    user_id: int
    username: str
    lang: Optional[str]
    pr_code: Optional[str]
    balance: float


@dataclass
class Channel:
    user_id: int
    channel_id: int
    channel_name: str
    hello_text_content: str
    photo: Optional[str]
    video: Optional[str]


@dataclass
class PrUser:
    user_id: int
    percent: float


@dataclass
class Wallets:
    user_id: int
    yoomoney: Optional[str]
    paypal: Optional[str]
    crypto: Optional[str]

    async def get_wallets_in_text(self, user_id: int) -> str:
        d = {
            'YooMoney': self.yoomoney,
            'PayPal': self.paypal,
            'Crypto': self.crypto
        }

        if set(d.values()) == {None}:
            return await _('Реквизиты не указаны😢', user_id)

        t = await _('🧾Ваши реквизиты🧾', user_id)
        return f'{t}\n' + '\n'.join([f"{key}: {value}" for key, value in d.items() if value])


class PaymentStatus(Enum):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


class PaymentType(Enum):
    YOOMONEY = 'YOOMONEY'
    PAYPAL = 'PAYPAL'
    CRYPTO = 'CRYPTO'


@dataclass
class Payment:
    user_id: int
    channel_id: int
    payment_uuid: str
    status: str
    time: int
    payment_type: PaymentType

    @staticmethod
    def new_payment(user_id: int, channel_id: int, payment_type: PaymentType):
        return Payment(
            user_id,
            channel_id,
            str(uuid.uuid4()),
            PaymentStatus.PENDING.value,
            int(time.time()),
            payment_type
        )


class LangChoice(Enum):
    RUSSIAN = 'rus'
    ENGLISH = 'eng'
    SPANISH = 'sp'
    CHINESE = 'ch'
