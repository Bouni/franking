import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from invio import Invio

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


class Mail:
    def __init__(self, subject: str, body: str):
        self.subject = subject
        self.body = body

    def send_invoice(self, invoice_id: str):
        invio = Invio()
        invoice_data = invio.get_invoice_data(invoice_id)
        invoice_pdf = invio.get_invoice_pdf(invoice_id)

        recipient = "bouni@owee.de"

        message = MIMEMultipart()
        message["Subject"] = self.subject
        message["From"] = EMAIL_SENDER
        message["To"] = recipient
        body_part = MIMEText(self.body)
        message.attach(body_part)

        part = MIMEApplication(
            invoice_pdf, Name=f"{invoice_data.get('invoiceNumber')}.pdf"
        )
        part["Content-Disposition"] = (
            f'attachment; filename="{invoice_data.get("invoiceNumber")}.pdf"'
        )
        message.attach(part)

        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipient, message.as_string())


if __name__ == "__main__":
    m = Mail("subject", "body")
    m.send_invoice("88f29f86-037a-4afe-9b9e-5d3ac9bd7c4c")
    # pdf = get_invoice_pdf("88f29f86-037a-4afe-9b9e-5d3ac9bd7c4c")
    # send_invoice("bouni@owee.de", "Invoice BSH-Boards", "Attached you find the invoice for your BSH-Board order.", "INV-2026-03-024", pdf)
