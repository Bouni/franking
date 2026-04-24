import datetime
import logging
import os
import pprint
import re
import time

from dotenv import load_dotenv
from fints.client import FinTS3PinTanClient, NeedTANResponse, SEPAAccount

load_dotenv()

SPK_BLZ = os.getenv("SPK_BLZ")
SPK_USER = os.getenv("SPK_USER")
SPK_PIN = os.getenv("SPK_PIN")
SPK_PRODUCT_ID = os.getenv("SPK_PRODUCT_ID")
SPK_IBAN = os.getenv("SPK_IBAN")
SPK_BIC = os.getenv("SPK_BIC")
SPK_ACCOUNT = os.getenv("SPK_ACCOUNT")
SPK_SUB_ACCOUNT = os.getenv("SPK_SUB_ACCOUNT")
SPK_BLZ = os.getenv("SPK_BLZ")
SPK_FINTS_PATH = os.getenv("SPK_FINTS_PATH", "fints_state.bin")

logging.basicConfig(level=logging.INFO)


class Sparkasse:
    def __init__(self):
        self.state_file = SPK_FINTS_PATH
        self.client = None

        if os.path.exists(self.state_file):
            with open(self.state_file, "rb") as f:
                self.client = FinTS3PinTanClient(
                    SPK_BLZ,
                    SPK_USER,
                    SPK_PIN,
                    "https://banking-bw1.s-fints-pt-bw.de/fints30",
                    from_data=f.read(),
                    product_id=SPK_PRODUCT_ID,
                )
        else:
            self.client = FinTS3PinTanClient(
                SPK_BLZ,
                SPK_USER,
                SPK_PIN,
                "https://banking-bw1.s-fints-pt-bw.de/fints30",
                product_id=SPK_PRODUCT_ID,
            )
            self.client.fetch_tan_mechanisms()
            self.client.set_tan_mechanism("923")

    def save_client_state(self):
        with open(self.state_file, "wb") as f:
            f.write(self.client.deconstruct(including_private=True))

    def get_invoice_number(self, purpose: str):
        r = re.search(r"INV-\d{4}-\d{2}-\d{3}", purpose)
        if r:
            return r.group(0)
        return ""

    def fetch_transactions(self):
        with self.client:
            if isinstance(self.client.init_tan_response, NeedTANResponse):
                if self.client.init_tan_response.decoupled:
                    print("Waiting for SPK App approval...")
                    while isinstance(self.client.init_tan_response, NeedTANResponse):
                        time.sleep(2)
                        self.client.init_tan_response = self.client.send_tan(
                            self.client.init_tan_response, None
                        )
                self.save_client_state()

            account = SEPAAccount(
                iban=SPK_IBAN,
                bic=SPK_BIC,
                accountnumber=SPK_ACCOUNT,
                subaccount=SPK_SUB_ACCOUNT,
                blz=SPK_BLZ,
            )
            transactions = self.client.get_transactions(
                account,
                datetime.date.today() - datetime.timedelta(days=30),
                datetime.date.today(),
            )

            transaction_data = []

            for transaction in transactions:
                if "INV" in transaction.data.get("purpose"):
                    transaction_data.append(
                        {
                            "invoice": self.get_invoice_number(
                                transaction.data.get("purpose")
                            ),
                            "name": transaction.data.get("applicant_name"),
                            "date": transaction.data.get("date"),
                            "amount": transaction.data.get("amount", {}).amount,
                        }
                    )

            return transaction_data

if __name__ == "__main__":
    spk = Sparkasse()
    spk.fetch_transactions()
