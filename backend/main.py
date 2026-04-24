import asyncio
import logging
import os
import textwrap
from pathlib import Path

import anyio
import pycountry
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pprint
from internetmarke import Internetmarke
from invio import Invio
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

logging.basicConfig(level=logging.INFO)

app = FastAPI()


@app.get("/api/payments/check")
async def check_payments():
    pp = PayPal()
    spk = Sparkasse()

    t1 = await anyio.to_thread.run_sync(pp.fetch_transactions)
    t2 = await anyio.to_thread.run_sync(spk.fetch_transactions)

    paid_numbers = {
        str(t.get("invoice")) for t in (t1 + t2) if t.get("invoice")
    }

    async with await Invio.create() as invio:
        paid_invoices = []
        raw_invoices = await invio.get_invoices()

        for i in raw_invoices:
            if i.get("status") == "sent":
                inv_num = str(i.get("invoiceNumber"))

                if inv_num in paid_numbers:
                    print(f"Match found: {inv_num}")
                    await invio.set_status_paid(i.get("id"))
                    paid_invoices.append({"id": i.get("id"), "invoiceNumber": i.get("invoiceNumber")})
                else:
                    print(f"No payment seen for: {inv_num}")

    return {"status": "success", "processed": len(raw_invoices), "paid": len(paid_invoices), "paid_invoices": paid_invoices}


@app.get("/api/invoices")
async def invoices():
    async with await Invio.create() as invio:
        raw_invoices = await invio.get_invoices()
        invoice_ids = [
            (i.get("id"), i.get("customerId"))
            for i in raw_invoices
            if i.get("status") in ("draft", "sent", "paid", "complete")
        ]

        async def fetch_full_invoice(inv_id, cust_id):
            inv_data, cust_data = await asyncio.gather(
                invio.get_invoice_data(inv_id), invio.get_customer_data(cust_id)
            )
            inv_data["customer"] = cust_data

            im = Path(LABEL_PATH) / f"{inv_data.get('invoiceNumber')}.png"
            inv_data["internetmarke"] = im.is_file()
            return inv_data

        invoices = await asyncio.gather(
            *[fetch_full_invoice(iid, cid) for iid, cid in invoice_ids]
        )

        invoices.sort(key=lambda x: x.get("invoiceNumber", 0), reverse=True)
        return {"invoices": invoices}


@app.get("/api/invoices/{invoice_id}/paid")
async def mark_invoice_paid(invoice_id):
    async with await Invio.create() as invio:
        await invio.set_status_paid(invoice_id)
    return JSONResponse({"success": True})


@app.post("/api/invoices/print")
async def print_invoice(data: dict):
    async with await Invio.create() as invio:
        invoice_pdf = await invio.get_invoice_pdf(data.get("invoice_id", ""))
    printer = BrotherMFC("192.168.88.21")
    await anyio.to_thread.run_sync(printer.print, invoice_pdf)
    return JSONResponse({"success": True})


@app.post("/api/invoices/email")
def send_invoice_email(data: dict):
    invio = Invio()
    invoice_data = invio.get_invoice_data(data.get("invoice_id", ""))
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

        P.S. Sorry to those of you who are non german speakers for the german invoice, my invoicing software does not yet allow localized invoices 😅
        """).strip()
    m = Mail(subject, body)
    m.send_invoice(data.get("invoice_id"))
    invio = Invio()
    invio.set_status_sent(data.get("invoice_id"))
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

    if data["countryCode"] == "DE":
        product_code = 21
    else:
        product_code = 10051

    im = Internetmarke()
    im.order(
        Path(LABEL_PATH), data["invoiceNumber"], address, product_code, dryrun=DEBUG
    )
    logging.info("Internetmarke purchased")
    return JSONResponse({"success": True, "msg": "Internetmarke purchased"})


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


app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Check if the requested path exists as a static file
    file_path = os.path.join("static", full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # Otherwise, return index.html to let Vue Router handle it
    return FileResponse("static/index.html")


# def get_db():
#     conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
#     conn.row_factory = sqlite3.Row
#     try:
#         yield conn
#     finally:
#         conn.close()
#
#
# @app.get("/", response_class=HTMLResponse)
# def index(
#     request: Request,
#     db: sqlite3.Connection = Depends(get_db),
# ):
#     im = Internetmarke()
#     cursor = db.cursor()
#     cursor.execute("""
#         SELECT
#             ii.invoice_id,
#             i.invoice_number,
#             ii.description,
#             ii.quantity,
#             ii.unit_price,
#             c.name,
#             c.contact_name,
#             c.address,
#             c.postal_code,
#             c.city,
#             c.country_code
#         FROM invoice_items ii
#         INNER JOIN invoices i ON ii.invoice_id = i.id
#         INNER JOIN customers c ON i.customer_id = c.id
#         WHERE ii.description LIKE '%Versand%' AND (i.status = 'sent' OR i.status = 'paid')
#         ORDER BY i.created_at DESC
#     """)
#     orders = [dict(order) for order in cursor.fetchall()]
#     for order in orders:
#         order["purchased"] = im.is_purchased(order["invoice_id"])
#     return templates.TemplateResponse(
#         request=request,
#         name="index.html",
#         context={"orders": orders, "balance": im.get_balance()},
#     )


#
#
# @app.get("/material/reserved")
# def reserved_material(
#     request: Request,
#     db: sqlite3.Connection = Depends(get_db),
# ):
#     cursor = db.cursor()
#     cursor.execute("""
#         SELECT
#             ii.description AS Article,
#             SUM(ii.quantity) || ' pcs' AS Total
#         FROM invoice_items ii
#         INNER JOIN invoices i ON ii.invoice_id = i.id
#         WHERE i.status = 'sent' AND ii.description NOT LIKE '%Versand%'
#         GROUP BY ii.description
#         ORDER BY SUM(ii.quantity) DESC;
#     """)
#     material = [dict(mat) for mat in cursor.fetchall()]
#     return templates.TemplateResponse(
#         "partials/material.html", {"request": request, "material": material}
#     )
#
#
# @app.post("/purchase/{invoice_id}")
# def purchase_internetmarke(
#     request: Request,
#     invoice_id: str,
#     response: Response,
#     product_code: int = Form(...),
#     db: sqlite3.Connection = Depends(get_db),
# ):
#     # fetch invoice data from db
#     im = Internetmarke()
#     cursor = db.cursor()
#     cursor.execute(f"""
#         SELECT
#             ii.invoice_id,
#             ii.description,
#             ii.quantity,
#             ii.unit_price,
#             c.name,
#             c.contact_name,
#             c.address,
#             c.postal_code,
#             c.city,
#             c.country_code
#         FROM invoice_items ii
#         INNER JOIN invoices i ON ii.invoice_id = i.id
#         INNER JOIN customers c ON i.customer_id = c.id
#         WHERE ii.description LIKE '%Versand%' AND
#         i.id = '{invoice_id}'
#     """)
#     invoice = cursor.fetchone()
#
#     if invoice:
#         invoice = dict(invoice)
#
#         # try converting 2-letter country code into 3-letter country code
#         if code := pycountry.countries.get(alpha_2=invoice["country_code"].upper()):
#             invoice["country_code"] = code.alpha_3
#         else:
#             payload = json.dumps(
#                 {
#                     "showToast": {
#                         "message": f"Invalid country code {invoice['country_code']}",
#                         "type": "debug",
#                     }
#                 }
#             )
#             response.headers["HX-Trigger"] = payload
#             response.status_code = status.HTTP_400_BAD_REQUEST
#             return response
#
#         # create address from data
#         address = Address(
#             name=invoice["name"],
#             address=invoice["address"],
#             city=invoice["city"],
#             postcode=invoice["postal_code"],
#             country=invoice["country_code"],
#         )
#
#         if not Path(LABEL_PATH).is_dir():
#             logging.error(f"Label path {LABEL_PATH} is not a directory")
#             payload = json.dumps(
#                 {
#                     "showToast": {
#                         "message": f"Label path ({LABEL_PATH}) does not exist! ",
#                         "type": "debug",
#                     }
#                 }
#             )
#             response.headers["HX-Trigger"] = payload
#             response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#             return response
#
#         im = Internetmarke()
#         if DEBUG:
#             logging.info("DEBUG active, Internetmarke dryrun")
#             payload = json.dumps(
#                 {
#                     "showToast": {
#                         "message": "Debug mode active, no Internetmarke purchased",
#                         "type": "debug",
#                     }
#                 }
#             )
#             response.headers["HX-Trigger"] = payload
#             response.status_code = status.HTTP_204_NO_CONTENT
#             return response
#         im.order(
#             Path(LABEL_PATH), invoice["invoice_id"], address, product_code, dryrun=DEBUG
#         )
#
#     invoice["purchased"] = im.is_purchased(invoice["invoice_id"])
#
#     return templates.TemplateResponse(
#         "partials/buttons.html", {"request": request, "order": invoice}
#     )
#
#
# @app.post("/print/{invoice_id}")
# def print_label(invoice_id: str, response: Response):
#     ql = BrotherQL()
#     lp = Path(LABEL_PATH) / f"{invoice_id}.png"
#     if not lp.is_file():
#         payload = json.dumps(
#             {
#                 "showToast": {
#                     "message": f"Label file ({lp}) does not exist!",
#                     "type": "failure",
#                 }
#             }
#         )
#         response.headers["HX-Trigger"] = payload
#         response.status_code = status.HTTP_404_NOT_FOUND
#         return response
#     if DEBUG:
#         logging.info("DEBUG active, printing label is skipped")
#         payload = json.dumps(
#             {
#                 "showToast": {
#                     "message": "Debug mode active, no label printed",
#                     "type": "debug",
#                 }
#             }
#         )
#         response.headers["HX-Trigger"] = payload
#         response.status_code = status.HTTP_204_NO_CONTENT
#         return response
#     else:
#         result = ql.print_label(lp)
#         if result:
#             payload = json.dumps(
#                 {
#                     "showToast": {
#                         "message": "Label sucessfully printed!",
#                         "type": "success",
#                     }
#                 }
#             )
#             response.headers["HX-Trigger"] = payload
#             response.status_code = status.HTTP_204_NO_CONTENT
#             return response
#         else:
#             payload = json.dumps(
#                 {
#                     "showToast": {
#                         "message": "Label print failed!",
#                         "type": "failure",
#                     }
#                 }
#             )
#             response.headers["HX-Trigger"] = payload
#             response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#             return response
#
#
# @app.post("/send/{invoice_id}")
# def send_invoice_email(invoice_id: str, response: Response):
#     invio = Invio()
#     invoice_data = invio.get_invoice_data(invoice_id)
#     subject = f"Invoice {invoice_data.get('invoiceNumber')} (BSH-Board)"
#     body = textwrap.dedent(f"""
#         Hi {invoice_data.get("customer", {}).get("name")},
#
#         Im Anhang findest du die Rechnung für deine Bestellung.
#         Diese beinhaltet Zahlungsinformationen für Banküberweisungen und PayPal.
#
#         Sobald ich die Zahlung erhalten habe versende ich in aller Regel am nächsten Werktag.
#
#         Wichtiger Hinweis: Ich bin bis zum 5. April im Urlaub, der Versand startet erst nach diesem Datum!
#
#         Vielen Dank für die Bestellung!
#
#         -------------------------------------------------------------------------------------
#
#         Attached you find the invoice for your order.
#         It contains payment info for bank transfer as well as for PayPal.
#
#         As soon as I recieved the payment, I'll pack your oder and send it usually by the next work day.
#
#         Important note: I'm on vaccation until April 5th, shipping will start after that date!
#
#         Thank you very much for your Order!
#
#         -------------------------------------------------------------------------------------
#
#
#         Bouni
#
#         P.S. Sorry to those of you who are non german speakers for the german invoice, my invoicing software does not yet allow localized invoices 😅
#         """).strip()
#     m = Mail(subject, body)
#     m.send_invoice(invoice_id)
#     payload = json.dumps(
#         {"showToast": {"message": "Invoice successfully sent!", "type": "success"}}
#     )
#     response.headers["HX-Trigger"] = payload
#     response.status_code = status.HTTP_204_NO_CONTENT
#     return response
