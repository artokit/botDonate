import base64
import hashlib
import json
import requests
from config import URL_POSTBACK, YOOMONEY_REDIRECT_URL, CRYPTOMUS_PAYMENT_KEY, CRYPTOMUS_MERCHANT_UUID

ALLOWED_CRYPTOCURRENCIES = [
    'AVAX',
    'BNB',
    'BTC',
    'BUSD',
    'ETH',
    'LTC',
    'MATIC',
    'SOL',
    'USDC',
    'USDT',
]


class CryptomusClient:
    @staticmethod
    def create_payment(order_id: str, amount: float, to_currency: str):
        data = {
            'amount': str(amount),
            'currency': "USD",
            'order_id': order_id,
            'url_return': YOOMONEY_REDIRECT_URL,
            'url_callback': URL_POSTBACK + 'crypt_payment/',
            'is_payment_multiple': True,
            'lifetime': '10800',
            'to_currency': to_currency
        }
        body_data, sign = CryptomusClient.crypt_data(data)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "merchant": CRYPTOMUS_MERCHANT_UUID,
            "sign": sign
        }
        r = requests.post('https://api.cryptomus.com/v1/payment', data=body_data, headers=headers)
        return r.json()

    @staticmethod
    def test_webhook(order_id: str):
        data = {
            'url_callback': URL_POSTBACK + 'crypt_payment/',
            'currency': 'USDT',
            'network': 'eth',
            'order_id': order_id,
            'status': 'paid'
        }
        body_data, sign = CryptomusClient.crypt_data(data)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "merchant": CRYPTOMUS_MERCHANT_UUID,
            "sign": sign
        }
        r = requests.post('https://api.cryptomus.com/v1/test-webhook/payment', data=body_data, headers=headers)
        print(r.json())

    @staticmethod
    def crypt_data(data):
        json_body_data = json.dumps(data, separators=(',', ':'))
        json_body_data_binary = json_body_data.encode('utf-8')
        encoded_data = base64.b64encode(json_body_data_binary)
        sign_md5_obj = hashlib.md5(encoded_data + CRYPTOMUS_PAYMENT_KEY.encode('utf-8'))
        return json_body_data, sign_md5_obj.hexdigest()


# c = CryptomusClient()
# print(c.create_payment('3afa51tq5553231', 35.5, 'USDT'))
# c.test_webhook('98af2547-1917-41fd-b02b-fecf51309ccc')
