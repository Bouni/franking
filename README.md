# franking

A [invio](https://github.com/kittendevv/Invio) sidecar project that allows me to perform various actions very fast.

- send invoice as an email attachment and mark invoice as sent
- mark invoice as paid
- public order form (order.bouni.de) that creates a draft invoice in Invio, including shipping costs from Sendcloud rounded up to the next full euro
- create shipping labels via [Sendcloud](https://www.sendcloud.com/)
  - DHL Kleinpaket for shipments within Germany
  - DHL Warenpost International Premium (with tracking) for international shipments
  - the default method can be overridden per invoice
  - the tracking link is emailed to the customer, the text is editable in the Settings tab (`{tracking_link}` marks where the link goes)
- the texts of the invoice and tracking emails are editable in the Settings tab, with placeholders like `{name}` and `{invoice_number}`
- print the DHL labels on a Brother QL-1110NWB (DK-11247, 103x164mm); older Internetmarken still print on a [Brother QL-710W](https://store.brother.ch/de-ch/devices/label-printer/ql/ql710w) (38mm endless)
- print the invoice on paper
- Integration with PayPal and Sparkasse (via FinTS) to fetch the latest payment data and update the payment status with that data

All data is read via the Invio API.

The whole project is rather hacky and not really customizable, but maybe someone finds it useful anyway :-)

<img width="1769" height="939" alt="franking" src="https://github.com/user-attachments/assets/056f9029-0882-4655-a59c-675816515259" />

The tech stack:

 - [FastAPI](https://fastapi.tiangolo.com/)
 - [Vue3](https://vuejs.org/)
 - [Vuetify](https://vuetifyjs.com/)
 - [Sendcloud API v3](https://sendcloud.dev/)
 - [python-inema](https://codeberg.org/gms/python-inema)
 - [brother_ql](https://github.com/pklaus/brother_ql)
 - [python-fints](github.com/raphaelm/python-fints)

