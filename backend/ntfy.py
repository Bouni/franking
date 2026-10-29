import base64
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

NTFY_URL = os.getenv("NTFY_URL")
NTFY_TOKEN = os.getenv("NTFY_TOKEN")


async def send_notification(
    title: str, message: str, tags: list[str] | None = None, priority: int = 1
):
    if not NTFY_URL:
        logging.info(f"NTFY_URL not set, notification not sent: {title}")
        return

    headers = {"Priority": str(priority)}

    if title:
        # Headers are ASCII only, ntfy decodes RFC 2047 encoded titles
        headers["Title"] = (
            title
            if title.isascii()
            else f"=?UTF-8?B?{base64.b64encode(title.encode()).decode()}?="
        )
    if tags:
        headers["Tags"] = ",".join(tags)
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            NTFY_URL, content=message.encode("utf-8"), headers=headers
        )
        response.raise_for_status()
