from json import JSONDecodeError
from typing import Optional

import requests

from config import YOOMONEY_CLIENT_ID, YOOMONEY_REDIRECT_URL
import json
import os
from yoomoney import Authorize, Client
from yoomoney import Quickpay


class CustomClient:
    def __init__(self):
        self.token = TokenFile.get_token_from_file()

        if not self.token:
            self.auth_request()
            TokenFile.save_token(self.token)

        self.client = Client(self.token)
        self.receiver = self.client.account_info().account

    def auth_request(self):
        Authorize(
            client_id=YOOMONEY_CLIENT_ID,
            redirect_uri=YOOMONEY_REDIRECT_URL,
            scope=["account-info",
                   "operation-history",
                   "operation-details",
                   "incoming-transfers",
                   "payment-p2p",
                   "payment-shop",
                   ]
        )
        self.token = input('Enter Access token again: ')

    def create_payment(self, label: str, amount: int) -> str:
        check = Quickpay(
            receiver=self.receiver,
            quickpay_form='shop',
            targets='Anonymous donate',
            paymentType='SB',
            sum=amount,
            label=label,
        )

        return check.redirected_url

    def check_payment(self, label: str) -> list:
        return self.client.operation_history(label=label).operations

    def pay_of_wallet(self, wallet: str, amount: float):
        r = requests.post(
            "https://yoomoney.ru/api/request-payment",
            headers={"Authorization": f"Bearer {self.token}", 'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'pattern_id': 'p2p',
                'to': wallet,
                'amount': amount,
            }
        )
        res = r.json()
        r = requests.post(
            'https://yoomoney.ru/api/process-payment',
            headers={"Authorization": f"Bearer {self.token}", 'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'request_id': res['request_id']
            }
        )


class TokenFile:
    TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token.json')

    @staticmethod
    def get_token_from_file() -> Optional[str]:
        with open(TokenFile.TOKEN_PATH) as f:
            try:
                return json.load(f)['token']

            except (FileNotFoundError, JSONDecodeError):
                return None

    @staticmethod
    def save_token(token) -> None:
        with open(TokenFile.TOKEN_PATH, 'w') as f:
            json.dump({'token': token}, f)


# c = CustomClient()
# c.pay_of_wallet('4100117785585742', 2)
