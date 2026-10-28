import logging
import os
from contextlib import asynccontextmanager
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import aioimaplib
import aiosmtplib
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", default="")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", default=465))
EMAIL_USER = os.getenv("EMAIL_USER", default="")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", default="")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", default="")

# IMAP folders for the copies of sent emails, created when missing
INVOICE_FOLDER = '"Gewerbe.Verschickte Rechnungen"'
TRACKING_FOLDER = '"Gewerbe.Verschickte Tracking"'

INVIO_URL = os.getenv("INVIO_URL", "")
INVIO_USER = os.getenv("INVIO_USER", "")
INVIO_PASSWORD = os.getenv("INVIO_PASSWORD", "")


class Mail:
    def __init__(
        self, subject: str, body: str, invoice_data: dict, attachment: bytes = b""
    ):
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

    def _message(self) -> MIMEMultipart:
        recipient = (self.invoice_data.get("customer") or {}).get("email")

        if not recipient:
            raise Exception("No mail address found")

        message = MIMEMultipart()
        message["Subject"] = self.subject
        message["From"] = EMAIL_SENDER
        message["To"] = recipient
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=EMAIL_SENDER.split("@")[-1])
        body_part = MIMEText(self.body)
        message.attach(body_part)
        return message

    async def _send(self, message: MIMEMultipart):
        await aiosmtplib.send(
            message,
            hostname=EMAIL_SMTP_SERVER,
            port=EMAIL_SMTP_PORT,
            username=EMAIL_USER,
            password=EMAIL_PASSWORD,
            use_tls=True,
        )

    async def _save_copy(self, message: MIMEMultipart, folder: str):
        """Store a copy of a sent email in an IMAP folder, creating it first
        if it doesn't exist yet"""
        async with self.imap_session() as imap:
            response = await imap.append(message.as_bytes(), folder)
            if response.result != "OK":
                await imap.create(folder)
                response = await imap.append(message.as_bytes(), folder)
            if response.result != "OK":
                logging.error(f"Failed to append to {folder}: {response.lines}")

    async def send_tracking(self):
        message = self._message()
        await self._send(message)
        logging.info(
            f"Tracking email for {self.invoice_data.get('invoiceNumber')} "
            f"sent to {message['To']}"
        )
        # The email is out, a missing copy must not report it as failed
        try:
            await self._save_copy(message, TRACKING_FOLDER)
        except Exception as e:  # noqa: BLE001
            logging.error(f"Copy of the tracking email not saved: {e}")

    async def send_invoice(self):
        message = self._message()
        recipient = message["To"]

        filename = f"{self.invoice_data.get('invoiceNumber')}.pdf"
        part = MIMEApplication(
            self.attachment,
            Name=filename,
            _subtype="pdf",
        )
        part.add_header("Content-Disposition", "attachment", filename=filename)

        message.attach(part)

        # send e-mail
        await self._send(message)
        logging.info(
            f"Invoice {self.invoice_data.get('invoice_id', '')} sent to {recipient}"
        )

        # Save to Sent folder
        await self._save_copy(message, INVOICE_FOLDER)
