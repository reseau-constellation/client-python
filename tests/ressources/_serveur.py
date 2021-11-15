import json
import sys

import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def traiter_message(message):
    message = json.loads(message)
    type_ = message["type"]
    id_ = message["id"]

    if type_ == "suivre":
        pass
    elif type_ == "action":
        return {
            "type": "action",
            "id": id_,
            "résultat": "Je suis un résultat",
        }
    else:
        raise ValueError(f"Type `{type_}` inconnu.")


async def serveur(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            réponse = await traiter_message(message)
            await ws.send_message(réponse)
        except ConnectionClosed:
            break


args = sys.argv[1:]
commande = args[0]

if commande == "version":
    print("1.0.0")
elif commande == "lancer":
    if len(args) >= 3:
        port = args[2]
    else:
        port = 5001

    async def main():
        print("Initialisation du serveur")
        sys.stdout.flush()
        async with trio.open_nursery() as pouponnière:
            await pouponnière.start(serve_websocket, serveur, 'localhost', int(port), None)
            print(f"Serveur prêt sur port : {port}")
            sys.stdout.flush()


    trio.run(main)
