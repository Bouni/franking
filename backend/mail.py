import logging
import os
from contextlib import asynccontextmanager
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aioimaplib
import aiosmtplib
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


class Mail:
    def __init__(self, subject: str, body: str, invoice_data: dict, attachment: bytes):
        self.subject = subject
        self.body = body
        self.invoice_data = invoice_data
        self.attachment = attachment

    @asynccontextmanager
    async def imap_session(self):
        imap = aioimaplib.IMAP4_SSL(EMAIL_SMTP_SERVER)
        try:
            await imap.wait_hello_from_server()
            await imap.login(EMAIL_USER, EMAIL_PASSWORD)
            yield imap
        finally:
            # Check if we are actually logged in/authenticated before trying to logout
            # The 'NONAUTH' state is where it sits after wait_hello but before login
            # The 'AUTH' or 'SELECTED' states are where logout is legal
            if imap.protocol and imap.protocol.state in ["AUTH", "SELECTED", "NONAUTH"]:
                try:
                    await imap.logout()
                except Exception as e:
                    logging.warning(f"Error during IMAP logout: {e}")

    async def send_invoice(self):
        recipient = self.invoice_data.get("customer", {}).get("email")

        if not recipient:
            raise Exception("No mail address found")

        message = MIMEMultipart()
        message["Subject"] = self.subject
        message["From"] = EMAIL_SENDER
        message["To"] = recipient
        body_part = MIMEText(self.body)
        message.attach(body_part)

        part = MIMEApplication(
            self.attachment, Name=f"{self.invoice_data.get('invoiceNumber')}.pdf"
        )
        part["Content-Disposition"] = (
            f'attachment; filename="{self.invoice_data.get("invoiceNumber")}.pdf"'
        )
        message.attach(part)

        # send e-mail
        await aiosmtplib.send(
            message,
            hostname=EMAIL_SMTP_SERVER,
            port=EMAIL_SMTP_PORT,
            username=EMAIL_USER,
            password=EMAIL_PASSWORD,
            use_tls=True,
        )
        logging.info(
            f"Invoice {self.invoice_data.get('invoice_id', '')} sent to {recipient}"
        )

        # Save to Sent folder
        async with self.imap_session() as imap:
            response = await imap.append(
                '"Gewerbe.Verschickte Rechnungen"', message.as_bytes()
            )
            if response.result != "OK":
                logging.error(f"Failed to append to Sent: {response.lines}")
