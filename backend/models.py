from pydantic import BaseModel
from typing import Optional


class Address(BaseModel):
    name: str
    address: str
    city: str
    postcode: str
    country: str
    phone: Optional[str] = None


class Item(BaseModel):
    name: str
    sku: str


class ItemList(BaseModel):
    items: list[Item]
