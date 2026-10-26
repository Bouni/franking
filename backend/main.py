import json
import logging
import os
import textwrap
from pathlib import Path

import anyio
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import order
from internetmarke import Internetmarke
from invio import Invio, InvioDB
from mail import Mail
from models import Address
from ntfy import send_notification
from paypal import PayPal
from printer import MFC_IP, BrotherMFC, debug_label, print_shipping_label
from sendcloud import (
    SENDCLOUD_DEFAULT_WEIGHT_G,
    Sendcloud,
    SendcloudError,
    shipping_option,
)
from sparkasse import Sparkasse

load_dotenv()

DEBUG = os.getenv("DEBUG", default="False").lower() in ("true", "1", "t")

logging.info(f"DEBUG = {DEBUG}")

LABEL_PATH = os.getenv("LABEL_PATH", default="/opt/docker/invio/labels")

BASE_PATH = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO)

app = FastAPI()


def label_info(invoice_number) -> dict | None:
    meta = Path(LABEL_PATH) / f"{invoice_number}.json"
    if not meta.with_suffix(".png").is_file():
        return None
    if meta.is_file():
        return json.loads(meta.read_text())
    # Internetmarke purchased before labels had metadata
    return {"printer": "ql710", "carrier": "internetmarke"}


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

        invoice_data["label"] = label_info(invoice_data.get("invoiceNumber"))

        return invoice_data


@app.get("/api/invoices")
async def invoices():
    async with InvioDB() as db:
        rows = await db.query_invoices()
        invoices = [json.loads(r["invoice_json"]) for r in rows]
        for i in invoices:
            i["label"] = label_info(i.get("invoiceNumber"))
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
    printer = BrotherMFC(MFC_IP)
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
        if DEBUG:
            recipient = (invoice_data.get("customer") or {}).get("email")
            logging.info(
                f"DEBUG active, invoice email not sent: '{subject}' to {recipient} "
                f"({len(invoice_pdf)} bytes PDF), status unchanged"
            )
            return JSONResponse({"success": True, "debug": True})
        m = Mail(subject, body, invoice_data, invoice_pdf)
        await m.send_invoice()
        # Re-sending must not move a paid/complete invoice back to "sent"
        if invoice_data.get("status") == "draft":
            await invio.set_status_sent(data.get("invoice_id"))
    return JSONResponse({"success": True})


@app.get("/api/internetmarke/balance")
async def internetmarke_balance():
    im = Internetmarke()
    return JSONResponse({"balance": im.get_balance()})


async def load_invoice(invoice_id: str) -> dict:
    async with await Invio.create() as invio:
        invoice_data = await invio.get_invoice_data(invoice_id)
        invoice_data["customer"] = await invio.get_customer_data(
            invoice_data.get("customerId")
        )
    return invoice_data


@app.post("/api/shipping/label")
async def create_shipping_label(data: dict):
    invoice_data = await load_invoice(data.get("invoice_id", ""))
    customer = invoice_data["customer"]
    invoice_number = invoice_data["invoiceNumber"]

    # Ship only after payment, and never twice
    if invoice_data.get("status") != "paid":
        return JSONResponse(
            {
                "success": False,
                "msg": f"Invoice {invoice_number} is {invoice_data.get('status')}, "
                "labels can only be bought for paid invoices.",
            }
        )
    if label_info(invoice_number) is not None:
        return JSONResponse(
            {"success": False, "msg": f"Invoice {invoice_number} already has a label."}
        )
    # DHL Kleinpaket within Germany, DHL Warenpost International Premium otherwise
    code = shipping_option(customer["countryCode"])
    weight_g = SENDCLOUD_DEFAULT_WEIGHT_G

    # The label is bought for the default weight, make sure the goods fit
    items_g = sum(
        (i.get("weightG") or 0) * (i.get("quantity") or 0)
        for i in invoice_data.get("items", [])
    )
    if items_g > weight_g:
        logging.info(
            f"{invoice_number}: items weigh {items_g:g}g, more than {weight_g}g"
        )
        return JSONResponse(
            {
                "success": False,
                "msg": f"Items weigh {items_g:g} g, which exceeds the label "
                f"weight of {weight_g} g (SENDCLOUD_DEFAULT_WEIGHT_G). "
                "No label was purchased.",
            }
        )

    label_path = Path(LABEL_PATH)
    if not label_path.is_dir():
        logging.error(f"Label path {LABEL_PATH} is not a directory")
        return JSONResponse(
            {"success": False, "msg": f"Label path ({LABEL_PATH}) does not exist!"}
        )

    address = Address(
        name=customer["name"],
        address=customer["address"],
        city=customer["city"],
        postcode=customer["postalCode"],
        country=customer["countryCode"],
        phone=customer.get("phone"),
        email=customer.get("email") or "",
    )

    # All Sendcloud labels are 103x164 for the QL-1110NWB. Older Internetmarken
    # keep "ql710" in their metadata and still print there.
    printer = "ql1110"

    if DEBUG:
        logging.info("DEBUG active, shipping label dryrun")
        debug_label(
            label_path / f"{invoice_number}.png",
            printer,
            [invoice_number, code, f"{customer['countryCode']} {weight_g}g"],
        )
        meta = {"printer": printer, "carrier": "debug", "shipping_option_code": code}
    else:
        try:
            async with Sendcloud() as sc:
                result = await sc.announce(invoice_data, address, code, weight_g)
        except SendcloudError as e:
            return JSONResponse({"success": False, "msg": str(e)})
        (label_path / f"{invoice_number}.png").write_bytes(result.pop("label"))
        meta = {"printer": printer, "shipping_option_code": code, **result}

    (label_path / f"{invoice_number}.json").write_text(json.dumps(meta))
    logging.info(f"Shipping label {code} created for {invoice_number}")
    return JSONResponse(
        {"success": True, "msg": f"Shipping label {code} created", "label": meta}
    )


@app.post("/api/shipping/print")
async def print_shipping(data: dict):
    invoice_number = data.get("invoice_number")
    label = Path(LABEL_PATH) / f"{invoice_number}.png"
    meta = label_info(invoice_number)
    if meta is None:
        logging.info(f"No shipping label found for invoice number {invoice_number}")
        return JSONResponse(
            {
                "success": False,
                "msg": f"No shipping label found for invoice number {invoice_number}",
            }
        )
    result = await anyio.to_thread.run_sync(
        print_shipping_label, label, meta["printer"]
    )
    if result:
        return JSONResponse({"success": True, "msg": "Shipping label printed"})
    logging.info("Printing failed")
    return JSONResponse({"success": False, "msg": "Printing failed"})


@app.post("/api/shipping/cancel")
async def cancel_shipping(data: dict):
    invoice_number = data.get("invoice_number")
    meta = label_info(invoice_number)
    if meta is None:
        return JSONResponse(
            {
                "success": False,
                "msg": f"No shipping label found for invoice number {invoice_number}",
            }
        )
    if meta.get("carrier") == "internetmarke":
        return JSONResponse(
            {
                "success": False,
                "msg": "Internetmarken can't be cancelled here, "
                "request a refund in the Portokasse",
            }
        )

    msg = "Debug label removed"
    if shipment_id := meta.get("shipment_id"):
        try:
            async with Sendcloud() as sc:
                result = await sc.cancel(shipment_id)
            msg = result.get("message", "Shipment cancelled")
        except SendcloudError as e:
            # Already cancelled (e.g. in the Sendcloud panel), clean up locally anyway
            if e.status_code != 409 or "already" not in str(e):
                return JSONResponse({"success": False, "msg": str(e)})
            msg = "Shipment was already cancelled"

    # Keep the cancelled label around, but out of the way
    label_path = Path(LABEL_PATH)
    for ext in ("png", "json"):
        f = label_path / f"{invoice_number}.{ext}"
        if f.is_file():
            f.rename(label_path / f"{invoice_number}.cancelled.{ext}")
    logging.info(f"Shipping label for {invoice_number} cancelled: {msg}")
    return JSONResponse({"success": True, "msg": msg})


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


@app.get("/api/order/shipping")
async def order_shipping(country: str):
    try:
        quote = await order.shipping_quote(country)
    except (SendcloudError, ValueError) as e:
        logging.error(f"Shipping quote for {country} failed: {e}")
        return JSONResponse({"success": False, "msg": "No shipping price available"})
    return JSONResponse(
        {"success": True, "name": quote["name"], "price": quote["price_rounded"]}
    )


@app.post("/api/order/submit")
async def submit_order(data: dict, request: Request):
    # Bots fill in the hidden "website" field, pretend everything worked
    if data.get("website"):
        logging.info("Order dropped by honeypot")
        return JSONResponse({"success": True})

    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.client.host
    )
    if order.rate_limited(client_ip):
        logging.info(f"Order rate limit hit by {client_ip}")
        return JSONResponse(
            {"success": False, "msg": "Too many orders, please try again later."},
            status_code=429,
        )

    async with await Invio.create() as invio:
        products = await invio.get_products()
        try:
            values, items = order.validate(data, products)
            quote = await order.shipping_quote(values["country"])
        except order.OrderError as e:
            return JSONResponse({"success": False, "msg": str(e)}, status_code=400)
        except (SendcloudError, ValueError) as e:
            logging.error(f"Shipping quote failed: {e}")
            return JSONResponse(
                {"success": False, "msg": "Could not calculate the shipping costs."},
                status_code=502,
            )

        items.append(
            order.shipping_item(products, values["country"], quote["price_rounded"])
        )
        customer_data = {
            "name": f"{values['firstname']} {values['lastname']}",
            "email": values["email"],
            "address": values["address"],
            "postalCode": values["postalcode"],
            "city": values["city"],
            "countryCode": values["country"],
        }
        total = sum(i["unitPrice"] * i["quantity"] for i in items)
        summary = "\n".join(f"{i['quantity']} x {i['description']}" for i in items)

        if DEBUG:
            logging.info(f"DEBUG active, no invoice created: {customer_data} {items}")
            return JSONResponse({"success": True, "debug": True, "total": total})

        customer = order.find_customer(await invio.get_customers(), customer_data)
        if customer is None:
            customer = await invio.create_customer(customer_data)
        invoice = await invio.create_invoice(
            {"customerId": customer["id"], "status": "draft", "items": items}
        )

    logging.info(f"Order {invoice.get('invoiceNumber')} from {customer_data['email']}")
    try:
        await send_notification(
            title=f"New order {invoice.get('invoiceNumber')}",
            message=f"{customer_data['name']} ({customer_data['countryCode']}), "
            f"{total:.2f} EUR\n{summary}",
            tags=["package"],
            priority=4,
        )
    except Exception as e:  # noqa: BLE001 - the order itself already worked
        logging.error(f"ntfy notification failed: {e}")

    return JSONResponse({"success": True, "total": total})


@app.post("/paypal/ipn")
async def paypal_ipn_listener(request: Request):

    form_data = await request.form()
    payload = dict(form_data)

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    verify_payload = {"cmd": "_notify-validate", **payload}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://ipnpb.paypal.com/cgi-bin/webscr", data=verify_payload
        )

    if response.text.strip() != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid IPN signature"
        )

    payment_status = payload.get("payment_status")

    if payment_status == "Completed":
        amount = payload.get("mc_gross")
        currency = payload.get("mc_currency")
        first_name = payload.get("first_name", "")
        last_name = payload.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()

        note = payload.get("memo") or payload.get("custom", "")

        logging.info(
            f"Direct Payment Received: {amount} {currency} from {full_name}. Note: {note}"
        )

        async with await Invio.create() as invio:
            raw_invoices = await invio.get_invoices()

            for i in raw_invoices:
                if i.get("status") == "sent":
                    inv_num = str(i.get("invoiceNumber"))
                    if inv_num in note:
                        logging.info(f"Match found: {inv_num} via PayPal (IPN)")
                        await invio.set_status_paid(i.get("id"), "PayPal")
                        await send_notification(
                            title="PayPal Payment received",
                            message=f"{amount} {currency} from {full_name}. Note: {note}",
                            tags=["money_with_wings"],
                            priority=5,
                        )

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
