import httpx 
from datetime import datetime, timedelta
import pprint
import os
from dotenv import load_dotenv
load_dotenv()

CLIENT_ID= os.getenv("PAYPAL_CLIENT_ID")
SECRET = os.getenv("PAYPAL_SECRET")

def get_paypal_transactions():
    with httpx.Client(base_url="https://api-m.paypal.com") as client:
        # 1. Get Access Token
        token_resp = client.post(
            "/v1/oauth2/token",
            auth=(CLIENT_ID, SECRET),
            data={"grant_type": "client_credentials"}
        )
        token = token_resp.json().get('access_token')

        # 2. Define Date Range
        start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # 3. Fetch Transactions
        headers = {"Authorization": f"Bearer {token}"}
        params = {"start_date": start, "end_date": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}
        
        response = client.get("/v1/reporting/transactions", headers=headers, params=params)


        return response.json()

data = get_paypal_transactions()

pprint.pprint(data)
