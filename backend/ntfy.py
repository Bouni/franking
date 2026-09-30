import os

import httpx
from dotenv import load_dotenv

load_dotenv()

NTFY_URL = os.getenv("NTFY_URL")
NTFY_TOKEN = os.getenv("NTFY_TOKEN")


async def send_notification(
    title: str, message: str, tags: list[str] | None = None, priority: int = 1
):
    headers = {}

    if title:
        headers["Title"] = title
        headers["Priority"] = str(priority)
    if tags:
        headers["Tags"] = ",".join(tags)
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            NTFY_URL, content=message.encode("utf-8"), headers=headers
        )
        response.raise_for_status()
