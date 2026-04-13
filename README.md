# franking

A [invio](https://github.com/kittendevv/Invio) sidecar project that allows me to perform various actions very fast.

- send invoice as an email attachment and mark invoice as sent
- mark invoice as paid
- purchase Deutsche Post [Internetmarken](https://shop.deutschepost.de/internetmarke) 
- print the Internetmarke on a [Brother QL-710W](https://store.brother.ch/de-ch/devices/label-printer/ql/ql710w)
- print the invoice on paper 

All data is read via the Invio API.

The whole project is rather hacky and not really customizable, but maybe someone finds it useful anyway :-)

<img width="2465" height="1055" alt="franking" src="https://github.com/user-attachments/assets/38fd12d0-2652-4489-b186-791d75df21c6" />

The tech stack:

 - [FastAPI](https://fastapi.tiangolo.com/)
 - [Vue3](https://vuejs.org/)
 - [Vuetify](https://vuetifyjs.com/)
 - [python-inema](https://codeberg.org/gms/python-inema)
 - [brother_ql](https://github.com/pklaus/brother_ql)

