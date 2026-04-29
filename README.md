# franking

A [invio](https://github.com/kittendevv/Invio) sidecar project that allows me to perform various actions very fast.

- send invoice as an email attachment and mark invoice as sent
- mark invoice as paid
- purchase Deutsche Post [Internetmarken](https://shop.deutschepost.de/internetmarke) 
- print the Internetmarke on a [Brother QL-710W](https://store.brother.ch/de-ch/devices/label-printer/ql/ql710w)
- print the invoice on paper
- Integration with PayPal and Sparkasse (via FinTS) to fetch the latest payment data and update the payment status with that data

All data is read via the Invio API.

The whole project is rather hacky and not really customizable, but maybe someone finds it useful anyway :-)

<img width="1769" height="939" alt="franking" src="https://github.com/user-attachments/assets/056f9029-0882-4655-a59c-675816515259" />

The tech stack:

 - [FastAPI](https://fastapi.tiangolo.com/)
 - [Vue3](https://vuejs.org/)
 - [Vuetify](https://vuetifyjs.com/)
 - [python-inema](https://codeberg.org/gms/python-inema)
 - [brother_ql](https://github.com/pklaus/brother_ql)
 - [python-fints](github.com/raphaelm/python-fints)

