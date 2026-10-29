import re
import httpx
from datetime import datetime, timedelta
import pprint
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
SECRET = os.getenv("PAYPAL_SECRET")


class PayPal:
    def __init__(self): ...

    def fetch_transactions(self, days: int = 30):
        with httpx.Client(base_url="https://api-m.paypal.com") as client:
            token_resp = client.post(
                "/v1/oauth2/token",
                auth=(CLIENT_ID, SECRET),
                data={"grant_type": "client_credentials"},
            )
            token = token_resp.json().get("access_token")
            start = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "start_date": start,
                "end_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": "all",
            }
            response = client.get(
                "/v1/reporting/transactions", headers=headers, params=params
            )
            return self.filter_transactions(
                response.json().get("transaction_details", [])
            )

    def get_invoice_number(self, purpose: str):
        r = re.search(r"INV-\d{4}-\d{2}-\d{3}", purpose)
        if r:
            return r.group(0)
        return ""

    def filter_transactions(self, transactions):
        """Completed transactions with an invoice number in the note, and
        incoming payments without one, which the payment check tries to match
        by email or name"""
        transaction_data = []
        for t in transactions:
            info = t.get("transaction_info", {})
            # S = completed, pending (P), denied (D) and reversed (V) don't count
            if info.get("transaction_status") != "S":
                continue
            note = info.get("transaction_note", "")
            amount = info.get("transaction_amount", {}).get("value", 0.0)
            if "INV" not in note and float(amount or 0) <= 0:
                continue
            payer = t.get("payer_info", {})
            transaction_data.append(
                {
                    "invoice": self.get_invoice_number(note),
                    "name": payer.get("payer_name", {}).get("alternate_full_name", ""),
                    "email": payer.get("email_address", ""),
                    "date": info.get("transaction_updated_date", ""),
                    "amount": amount,
                }
            )
        return transaction_data


if __name__ == "__main__":
    paypal = PayPal()
    pprint.pprint(paypal.fetch_transactions())
