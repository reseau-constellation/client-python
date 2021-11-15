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


def écrire_à_stdout(message: str):
    print(message)
    sys.stdout.flush()


if commande == "version":
    écrire_à_stdout("1.0.0")
elif commande == "lancer":

    port = args[2] if len(args) >= 3 else None


    async def main():
        écrire_à_stdout("Initialisation du serveur")
        port_ = port or 5000

        async with trio.open_nursery() as pouponnière:
            async def _lancer_port_ws(p):
                await pouponnière.start(serve_websocket, serveur, 'localhost', int(p), None)

            if port:
                await _lancer_port_ws(port_)
            else:
                while True:
                    try:
                        await _lancer_port_ws(port_)
                        break
                    except OSError as e:
                        if e.args[1] == "Address already in use":
                            port_ += 1
                        else:
                            raise e
            écrire_à_stdout(f"Serveur prêt sur port : {port_}")
            sys.stdout.flush()


    trio.run(main)
