import logging
import os

from dotenv import load_dotenv
from fints.client import FinTS3PinTanClient

load_dotenv()

SPK_BLZ = os.getenv("SPK_BLZ")
SPK_USER = os.getenv("SPK_USER")
SPK_PIN = os.getenv("SPK_PIN")
SPK_PRODUCT_ID = os.getenv("SPK_PRODUCT_ID")

logging.basicConfig(level=logging.DEBUG)
f = FinTS3PinTanClient(
    SPK_BLZ,  # Your bank's BLZ
    SPK_USER,  # Your login name
    SPK_PIN,  # Your banking PIN
    "https://hbci-pintan.gad.de/cgi-bin/hbciservlet",
    product_id=SPK_PRODUCT_ID,  # see above
)
