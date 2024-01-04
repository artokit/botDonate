from abc import ABCMeta, abstractmethod
from database import db_api
from database.db_models import Payment
from payments.youmoney import yoomoney_api
from payments.paypal import paypal_api
from payments.cryptomus import cryptomus_api


class PaymentManager(metaclass=ABCMeta):
    def __init__(self, service):
        self.service = service

    @abstractmethod
    def create_payment(self, *args, **kwargs):
        pass


class YoomoneyPayment(PaymentManager):
    def __init__(self):
        PaymentManager.__init__(self, yoomoney_api.CustomClient())

    async def create_payment(self, *args, **kwargs) -> str:
        await db_api.add_payment(kwargs['payment'])
        url = self.service.create_payment(kwargs['label'], kwargs['amount'])
        return url

    async def pay_of_to(self, wallet: str, amount: float):
        self.service.pay_of_wallet(wallet, amount)


class PayPalPayment(PaymentManager):
    def __init__(self):
        PaymentManager.__init__(self, paypal_api.PayPalClient())

    async def create_payment(self, *args, **kwargs) -> str:
        # await db_api.add_payment(kwargs['payment'])
        return self.service.create_payment(kwargs['amount'])

    async def check_payment(self, payment_uuid: str):
        await self.service.check_payment(payment_uuid)

    async def execute_payment(self, payment_id: str, payer_id: str):
        await self.service.execute_payment(payment_id, payer_id)
        return await self.service.get_info_payment(payment_id)


class CryptomusPayment(PaymentManager):
    def __init__(self):
        PaymentManager.__init__(self, cryptomus_api.CryptomusClient())

    async def create_payment(self, *args, **kwargs):
        payment: Payment = kwargs['payment']
        await db_api.add_payment(payment)
        return self.service.create_payment(payment.payment_uuid, kwargs['amount'], kwargs['to_currency'])


YOOMONEY_CLIENT = YoomoneyPayment()
PAYPAL_CLIENT = PayPalPayment()
CRYPTOMUS_CLIENT = CryptomusPayment()
