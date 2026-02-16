# franking

A [invio](https://github.com/kittendevv/Invio) sidecar project that allows to purchase Deutsche Post [Internetmarken](https://shop.deutschepost.de/internetmarke) and print them on a [Brother QL-710W](https://store.brother.ch/de-ch/devices/label-printer/ql/ql710w).

It reads the Invio sqlite3 database to fetch all orders that have a item with "Versand" in the description and shows them as a simple list with buttons for selcting the product type (national or international up to 500g), a button for purchasing the Internetmarke and one for printing the actual label.

The whole project is rather hacky and not really customizable, but maybe someone finds it useful anyway :-)

<img width="2465" height="1055" alt="franking" src="https://github.com/user-attachments/assets/38fd12d0-2652-4489-b186-791d75df21c6" />

The tech stack:

 - [FastAPI](https://fastapi.tiangolo.com/)
 - [HTMX](https://htmx.org/)
 - [python-inema](https://codeberg.org/gms/python-inema)
 - [brother_ql](https://github.com/pklaus/brother_ql)

