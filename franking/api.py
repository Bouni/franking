import os

import inema.rest as ir
from dotenv import load_dotenv
from inema.data import products

from franking.models import Address

load_dotenv()

DHL_API_KEY = os.getenv("DHL_API_KEY")
DHL_API_SECRET = os.getenv("DHL_API_SECRET")
PORTOKASSE_USER = os.getenv("PORTOKASSE_USER")
PORTOKASSE_PASS = os.getenv("PORTOKASSE_PASS")

SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_ADDRESS = os.getenv("SENDER_ADDRESS")
SENDER_POSTCODE = os.getenv("SENDER_POSTCODE")
SENDER_CITY = os.getenv("SENDER_CITY")
SENDER_COUNTRY = os.getenv("SENDER_COUNTRY")

# Notes:
# Format 216 = Brother DK-22225 Endlos-Etikett 38mm
# Product 21 = Großbrief
# Product 10051 = Großbrief Intern. GK


class Internetmarke:
    def __init__(self):
        self.sender = Address(
            name=SENDER_NAME,
            address=SENDER_ADDRESS,
            city=SENDER_CITY,
            postcode=SENDER_POSTCODE,
            country=SENDER_COUNTRY,
        )
        self.session = ir.Session(
            client=DHL_API_KEY,
            secret=DHL_API_SECRET,
            user=PORTOKASSE_USER,
            password=PORTOKASSE_PASS,
        )

    def get_balance(self):
        return self.session.balance

    def get_formats(self):
        return [
            format
            for format in self.session.get_formats()
            if "brother" in format["name"].lower()
        ]

    def get_products(self):
        return products.items()

    def check_health(self):
        return ir.check_health()

    def user_profile(self):
        return self.session.profile()

    def order(self, receiver: Address, product: int):
        oid = self.session.create_order()
        p = ir.mk_png_pos(
            product,
            sender=ir.mk_addr(
                name=self.sender.name,
                line=self.sender.address,
                postcode=self.sender.postcode,
                city=self.sender.city,
                country=self.sender.country,
            ),
            receiver=ir.mk_addr(
                name=receiver.name,
                line=receiver.address,
                postcode=receiver.postcode,
                city=receiver.city,
                country=receiver.country,
            ),
        )
        t = ir.calc_total(p)
        body = ir.mk_png_req(oid, p, t)
        fn = "label.zip"
        d = self.session.checkout_png(body, fn)
        return {"oid": oid, "p": p, "t": t, "fn": fn, "d": d}
