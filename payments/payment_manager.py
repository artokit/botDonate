import time
from abc import ABCMeta, abstractmethod
import db_api
from db_models import PaymentStatus
from payments.youmoney import yoomoney_api
from payments.paypal import paypal_api


class PaymentManager(metaclass=ABCMeta):
    def __init__(self, service):
        self.service = service

    @abstractmethod
    def check_payment(self, *args, **kwargs):
        pass

    @abstractmethod
    def create_payment(self, *args, **kwargs):
        pass


class YoomoneyPayment(PaymentManager):
    def __init__(self):
        PaymentManager.__init__(self, yoomoney_api.CustomClient())

    def check_payment(self, *args, **kwargs) -> PaymentStatus:
        history = self.service.check_payment(kwargs['label'])
        time_expired = 60 * 60 * 3

        if not history and (time.time() - kwargs['time'] >= time_expired):
            return PaymentStatus.CANCELLED

        if history:
            return PaymentStatus.COMPLETED

        return PaymentStatus.PENDING

    async def create_payment(self, *args, **kwargs) -> str:
        await db_api.add_payment(kwargs['payment'])
        url = self.service.create_payment(kwargs['label'], kwargs['amount'])
        return url


class PayPalPayment(PaymentManager):
    def __init__(self):
        PaymentManager.__init__(self, paypal_api.PayPalClient())

    async def create_payment(self, *args, **kwargs) -> str:
        await db_api.add_payment(kwargs['payment'])
        return self.service.create_payment(kwargs['amount'])

    def check_payment(self, *args, **kwargs):
        pass


YOOMONEY_CLIENT = YoomoneyPayment()
PAYPAL_CLIENT = PayPalPayment()
# i = uuid.uuid4()
# YOOMONEY_CLIENT.create_payment(label=i, amount=5)
# while True:
#     YOOMONEY_CLIENT.check_payment(label=i)
