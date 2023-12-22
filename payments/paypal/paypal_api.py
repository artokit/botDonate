import paypalrestsdk
from config import CLIENT_ID_PAYPAL, CLIENT_SECRET_PAYPAL


class PayPalClient:
    def __init__(self):
        self.client_id = CLIENT_ID_PAYPAL
        self.secret_key = CLIENT_SECRET_PAYPAL
        paypalrestsdk.configure({
            "mode": "sandbox",  # sandbox or live
            "client_id": self.client_id,
            "client_secret": self.secret_key
        })

    def create_payment(self, amount: int) -> str:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "http://localhost:3000/payment/execute",
                "cancel_url": "http://localhost:3000/"},
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
                "description": "This is the payment transaction description."}]})

        if payment.create():
            print("Payment created successfully")
        else:
            print(payment.error)
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = str(link.href)
                return approval_url


# PAYPAL = PayPalClient()
# # print(p.create_payment(10))
# # print(p.create_payment(10))
