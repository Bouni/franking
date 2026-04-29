import re
import httpx
from datetime import datetime, timedelta
import pprint
import os
from dotenv import load_dotenv
load_dotenv()

CLIENT_ID= os.getenv("PAYPAL_CLIENT_ID")
SECRET = os.getenv("PAYPAL_SECRET")

class PayPal:
   
    def __init__(self):
        ...

    def fetch_transactions(self, days:int=30):
        with httpx.Client(base_url="https://api-m.paypal.com") as client:
            token_resp = client.post(
                "/v1/oauth2/token",
                auth=(CLIENT_ID, SECRET),
                data={"grant_type": "client_credentials"}
            )
            token = token_resp.json().get('access_token')
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            headers = {"Authorization": f"Bearer {token}"}
            params = {"start_date": start, "end_date": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'), "fields": "all"} 
            response = client.get("/v1/reporting/transactions", headers=headers, params=params)
            return self.filter_transactions(response.json().get("transaction_details",[]))

    def get_invoice_number(self, purpose: str):
        r = re.search(r"INV-\d{4}-\d{2}-\d{3}", purpose)
        if r:
            return r.group(0)
        return ""

    def filter_transactions(self, transactions):
        transaction_data = []
        for t in transactions:
            if "INV" in t.get("transaction_info", {}).get("transaction_note"):
                transaction_data.append({
                    "invoice": self.get_invoice_number(t.get("transaction_info", {}).get("transaction_note", "")),
                    "name": t.get("payer_info", {}).get("payer_name",{}).get("alternate_full_name", ""),
                    "date": t.get("transaction_info", {}).get("transaction_updated_date", ""),  
                    "amount": t.get("transaction_info", {}).get("transaction_amount", {}).get("value", 0.0),
                    })
        return transaction_data

if __name__ == "__main__":
    paypal = PayPal()
    pprint.pprint(paypal.fetch_transactions())
