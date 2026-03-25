import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_PATH = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO)

EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", default="")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", default=465))
EMAIL_USER = os.getenv("EMAIL_USER", default="")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", default="")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", default="")

INVIO_URL = os.getenv("INVIO_URL", "")
INVIO_USER = os.getenv("INVIO_USER", "")
INVIO_PASSWORD = os.getenv("INVIO_PASSWORD", "")


def send_invoice(recipient: str, subject: str, body: str, invoice_number: str, invoice_data: bytes):
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = EMAIL_SENDER
    message["To"] = recipient
    body_part = MIMEText(body)
    message.attach(body_part)
    
    part = MIMEApplication(invoice_data, Name=f"{invoice_number}.pdf")
    part['Content-Disposition'] = f'attachment; filename="{invoice_number}.pdf"'
    message.attach(part)


    with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipient, message.as_string())


def get_invoice_pdf(invoice_id: str):
    r = requests.post(
        f"{INVIO_URL}/auth/login",
        json={"username": INVIO_USER, "password": INVIO_PASSWORD},
    )
    token = r.json()["token"]
    r = requests.get(
        f"{INVIO_URL}/invoices/{invoice_id}/pdf",
        stream=True,
        headers={"Authorization": f"Bearer {token}"},
    ) 
    r.raise_for_status()
    return r.content


if __name__ == "__main__":
    pdf = get_invoice_pdf("88f29f86-037a-4afe-9b9e-5d3ac9bd7c4c")
    send_invoice("bouni@owee.de", "Invoice BSH-Boards", "Attached you find the invoice for your BSH-Board order.", "INV-2026-03-024", pdf)
