from typing import Optional

import paypalrestsdk
from config import CLIENT_ID_PAYPAL, CLIENT_SECRET_PAYPAL, URL_POSTBACK


class PayPalClient:
    def __init__(self):
        self.client_id = CLIENT_ID_PAYPAL
        self.secret_key = CLIENT_SECRET_PAYPAL
        paypalrestsdk.configure({
            "mode": "live",  # sandbox or live
            "client_id": self.client_id,
            "client_secret": self.secret_key
        })

    def create_payment(self, amount: int) -> Optional[str]:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"},
            "redirect_urls": {
                "return_url": URL_POSTBACK + 'paypal/',
                "cancel_url": URL_POSTBACK + 'paypal/'},
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "item",
                        "sku": "item",
                        "price": amount,
                        "currency": "USD",
                        "quantity": 1}]},
                "amount": {
                    "total": amount,
                    "currency": "USD"},
                "description": "Donation"}]})
        # print(payment)
        # payment_history = paypalrestsdk.Payment.all()
        # print(payment_history)
        # print(payment.request_id)
        # payment = paypalrestsdk.Payment.find(payment.request_id)

        # if payment.execute({"payer_id": "DUFRQ8GWYMJXC"}):
        #     print("Payment execute successfully")
        # else:
        #     print(payment.error)  # Error Hash
        # print(payment_history)
        if payment.create():
            print("Payment created successfully")
        else:
            return
            # print(payment.error)
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = str(link.href)
                return approval_url

    async def execute_payment(self, payment_id: str, payer_id: str):
        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            print("Payment execute successfully")
        else:
            print(payment.error)  # Error Hash

    async def get_info_payment(self, payment_id: str):
        payment = paypalrestsdk.Payment.find(payment_id)
        return payment


# PAYPAL = PayPalClient()
# PAYPAL.execute_payment('PAYID-MWLKHRI43K20969UY086870R', '8SCTTS8FC3TF2')
# print(PAYPAL.create_payment(10, 'wetw'))
# # print(p.create_payment(10))
