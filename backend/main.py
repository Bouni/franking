import json
import logging
import os
import pprint
import textwrap
from pathlib import Path

import anyio
import httpx
import pycountry
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from internetmarke import Internetmarke
from invio import Invio, InvioDB
from mail import Mail
from models import Address
from paypal import PayPal
from printer import BrotherMFC, BrotherQL
from sparkasse import Sparkasse

load_dotenv()

DEBUG = os.getenv("DEBUG", default="False").lower() in ("true", "1", "t")

logging.info(f"DEBUG = {DEBUG}")

LABEL_PATH = os.getenv("LABEL_PATH", default="/opt/docker/invio/labels")

BASE_PATH = Path(__file__).resolve().parent.parent

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID")
PAYPAL_BASE_URL = "https://api-m.paypal.com"

logging.basicConfig(level=logging.INFO)

app = FastAPI()


@app.get("/api/payments/check")
async def check_payments():
    pp = PayPal()
    spk = Sparkasse()

    t1 = await anyio.to_thread.run_sync(pp.fetch_transactions)
    t2 = await anyio.to_thread.run_sync(spk.fetch_transactions)

    payments_map = {}

    for t in t1:
        if inv := t.get("invoice"):
            payments_map[str(inv)] = "PayPal"

    for t in t2:
        if inv := t.get("invoice"):
            payments_map[str(inv)] = "Bank Transfer"

    async with await Invio.create() as invio:
        paid_invoices = []
        raw_invoices = await invio.get_invoices()

        for i in raw_invoices:
            if i.get("status") == "sent":
                inv_num = str(i.get("invoiceNumber"))

                if inv_num in payments_map:
                    method = payments_map[inv_num]
                    print(f"Match found: {inv_num} via {method}")
                    await invio.set_status_paid(i.get("id"), method)
                    invoice_data = await invio.get_invoice_data(i.get("id"))
                    paid_invoices.append(
                        {
                            "id": i.get("id"),
                            "invoiceNumber": i.get("invoiceNumber"),
                            "method": method,
                            "invoice_data": invoice_data,
                        }
                    )
                else:
                    print(f"No payment seen for: {inv_num}")

    return {
        "status": "success",
        "processed": len(raw_invoices),
        "paid": len(paid_invoices),
        "paid_invoices": paid_invoices,
    }


@app.get("/api/invoices/{invoice_id}")
async def get_invoice(invoice_id: str):
    async with await Invio.create() as invio:
        invoice_data = await invio.get_invoice_data(invoice_id)
        customer_data = await invio.get_customer_data(invoice_data.get("customerId"))

        invoice_data["customer"] = customer_data

        im = Path(LABEL_PATH) / f"{invoice_data.get('invoiceNumber')}.png"
        invoice_data["internetmarke"] = im.is_file()

        return invoice_data


@app.get("/api/invoices")
async def invoices():
    async with InvioDB() as db:
        rows = await db.query_invoices()
        invoices = [json.loads(r["invoice_json"]) for r in rows]
        invoices.sort(key=lambda x: x.get("invoiceNumber", 0), reverse=True)
        return {"invoices": invoices}


@app.post("/api/invoices/mark/paid")
async def mark_invoice_paid(data: dict):
    async with await Invio.create() as invio:
        await invio.set_status_paid(data.get("invoice_id", ""), data.get("method", ""))
    return JSONResponse({"success": True})


@app.post("/api/invoices/mark/complete")
async def mark_invoice_complete(data: dict):
    async with await Invio.create() as invio:
        await invio.set_status_complete(data.get("invoice_id", ""))
    return JSONResponse({"success": True})


@app.post("/api/invoices/print")
async def print_invoice(data: dict):
    async with await Invio.create() as invio:
        invoice_pdf = await invio.get_invoice_pdf(data.get("invoice_id", ""))
    printer = BrotherMFC("192.168.88.21")
    await anyio.to_thread.run_sync(printer.print, invoice_pdf)
    return JSONResponse({"success": True})


@app.post("/api/invoices/email")
async def send_invoice_email(data: dict):
    async with await Invio.create() as invio:
        invoice_data = await invio.get_invoice_data(data.get("invoice_id", ""))
        subject = f"Invoice {invoice_data.get('invoiceNumber')} (BSH-Board)"
        body = textwrap.dedent(f"""
            Hi {invoice_data.get("customer", {}).get("name")},
    
            Im Anhang findest du die Rechnung für deine Bestellung.
            Diese beinhaltet Zahlungsinformationen für Banküberweisungen und PayPal.
    
            Sobald ich die Zahlung erhalten habe versende ich in aller Regel am nächsten Werktag.
    
            Vielen Dank für die Bestellung!
    
            -------------------------------------------------------------------------------------
    
            Attached you find the invoice for your order.
            It contains payment info for bank transfer as well as for PayPal.
    
            As soon as I recieved the payment, I'll pack your oder and send it usually by the next work day.
    
            Thank you very much for your Order!
    
            -------------------------------------------------------------------------------------

            Bouni

            P.S. Sorry to those of you who are non german speakers, my invoicing software is limited when it comes to localization and you might get the invoice not in yor language but in german or english 😅
            """).strip()
        invoice_pdf = await invio.get_invoice_pdf(data.get("invoice_id", ""))
        m = Mail(subject, body, invoice_data, invoice_pdf)
        await m.send_invoice()
        await invio.set_status_sent(data.get("invoice_id"))
    return JSONResponse({"success": True})


@app.get("/api/internetmarke/balance")
async def internetmarke_balance():
    im = Internetmarke()
    return JSONResponse({"balance": im.get_balance()})


@app.post("/api/internetmarke/purchase")
def purchase_internetmarke(data: dict):
    if code := pycountry.countries.get(alpha_2=data["countryCode"].upper()):
        data["countryCode"] = code.alpha_3
    else:
        return JSONResponse({"success": False, "msg": "Failed to convert contry code"})

    # create address from data
    address = Address(
        name=data["name"],
        address=data["address"],
        city=data["city"],
        postcode=data["postalCode"],
        country=data["countryCode"],
        extra=data.get("phone"),
    )

    if not Path(LABEL_PATH).is_dir():
        logging.error(f"Label path {LABEL_PATH} is not a directory")
        return JSONResponse(
            {"success": False, "msg": f"Label path ({LABEL_PATH}) does not exist!"}
        )

    if DEBUG:
        logging.info("DEBUG active, Internetmarke dryrun")
        return JSONResponse(
            {"success": True, "msg": "Debug mode active, no Internetmarke purchased"}
        )

    if data["countryCode"] == "DEU":
        product_code = 21
        product_type = "Grossbrief national"
    else:
        product_code = 10051
        product_type = "Grossbrief international"
    logging.info(f"Internetmarke {product_type} purchased")
    im = Internetmarke()
    im.order(
        Path(LABEL_PATH), data["invoiceNumber"], address, product_code, dryrun=DEBUG
    )
    return JSONResponse(
        {"success": True, "msg": f"Internetmarke {product_type} purchased"}
    )


@app.post("/api/internetmarke/print")
async def print_internetmarke(data: dict):
    ql = BrotherQL()
    invoice_number = data.get("invoice_number")
    label = Path(LABEL_PATH) / f"{invoice_number}.png"
    if not label.is_file():
        logging.info(f"No Internetmarke found for invoice number {invoice_number}")
        return JSONResponse(
            {
                "success": False,
                "msg": "No Internetmarke found for invoice number {invoice_number}",
            }
        )
    result = ql.print_label(label)
    if result:
        logging.info("Internetmarke purchased")
        return JSONResponse({"success": True, "msg": "Internetmarke printed"})
    else:
        logging.info("Printing failed")
        return JSONResponse({"success": False, "msg": "Printing failed"})


@app.get("/api/order/products")
async def get_products():
    async with await Invio.create() as invio:
        products = await invio.get_products()
        products = [
            {
                k: v
                for k, v in p.items()
                if k
                not in [
                    "description",
                    "sku",
                    "unit",
                    "isActive",
                    "createdAt",
                    "updatedAt",
                ]
            }
            for p in products
        ]
        return products


@app.post("/webhooks/paypal")
async def paypal_webhook(request: Request):
    payload = await request.json()

    async with httpx.AsyncClient() as client:
        # 1. Get Access Token
        token_res = await client.post(
            f"{PAYPAL_BASE_URL}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
            data={"grant_type": "client_credentials"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=500, detail="Auth failed")

        token = token_res.json()["access_token"]

        # 2. Verify Webhook Signature
        verify_res = await client.post(
            f"{PAYPAL_BASE_URL}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "transmission_id": request.headers.get("paypal-transmission-id"),
                "transmission_time": request.headers.get("paypal-transmission-time"),
                "cert_url": request.headers.get("paypal-cert-url"),
                "auth_algo": request.headers.get("paypal-auth-algo"),
                "transmission_sig": request.headers.get("paypal-transmission-sig"),
                "webhook_id": PAYPAL_WEBHOOK_ID,
                "webhook_event": payload,
            },
        )

    if verify_res.json().get("verification_status") != "SUCCESS":
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 3. Handle your event synchronously
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})

    pprint.pprint(payload)

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        payment_id = resource.get("id")
        # Do your quick logic here (e.g., mark order paid in DB)
        print(f"Received payment for {payment_id}")

    return {"status": "ok"}


app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Check if the requested path exists as a static file
    file_path = os.path.join("static", full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # Otherwise, return index.html to let Vue Router handle it
    return FileResponse("static/index.html")
