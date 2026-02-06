from pydantic import BaseModel


class Address(BaseModel):
    name: str
    address: str
    city: str
    postcode: str
    country: str


class Item(BaseModel):
    name: str
    sku: str


class ItemList(BaseModel):
    items: list[Item]
