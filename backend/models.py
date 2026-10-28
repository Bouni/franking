from pydantic import BaseModel


class Address(BaseModel):
    name: str
    address: str = ""
    city: str
    postcode: str
    country: str
    region: str = ""  # state/province code, e.g. CA, NSW, ON
    phone: str | None = None
    email: str = ""
