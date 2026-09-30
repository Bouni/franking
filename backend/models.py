from pydantic import BaseModel


class Address(BaseModel):
    name: str
    address: str = ""
    street: str = ""
    housenumber: str = ""
    city: str
    postcode: str
    country: str
    phone: str | None = None
    email: str = ""


class Item(BaseModel):
    name: str
    sku: str


class ItemList(BaseModel):
    items: list[Item]
