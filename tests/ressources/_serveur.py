import io
import json
import sys

import click
import trio
from click_default_group import DefaultGroup
from trio_websocket import serve_websocket, ConnectionClosed, WebSocketConnection

try:
    from constellationPy.const import V_SERVEUR_NÉCESSAIRE, V_IPA_NÉCESSAIRE
except ModuleNotFoundError:
    # Pour tests sur Ubuntu... je ne suis pas sûr pourquoi ça ne fonctionne pas...
    V_SERVEUR_NÉCESSAIRE = "^0.3.5"
    V_IPA_NÉCESSAIRE = "^0.9.13"

_données = {}

# Nécessaire pour Windows
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')


def erreur_fonction_non_définie(message):
    return {
        "type": "erreur",
        "id": message["id"],
        "erreur": f"Fonction `Client.{'.'.join(message['fonction'])}()` n'existe pas ou n'est pas une fonction."
    }


async def envoyer_message_à_ws(message, ws: WebSocketConnection):
    await ws.send_message(json.dumps(message))


class Suiveur(object):
    def __init__(soimême):
        soimême.connexions = {}
        soimême.valeur = None

    async def suivre(soimême, id_, ws):
        soimême.connexions[id_] = ws
        await envoyer_message_à_ws({
            "type": "suivre",
            "id": id_,
            "données": soimême.valeur
        }, ws)

    def oublier(soimême, id_):
        soimême.connexions.pop(id_)

    async def changerValeur(soimême, val):
        soimême.valeur = val
        for id_, ws in soimême.connexions.items():
            await envoyer_message_à_ws({
                "type": "suivre",
                "id": id_,
                "données": soimême.valeur
            }, ws)

    def __contains__(soimême, item):
        return item in soimême.connexions


class Chercheur(object):
    def __init__(soimême):
        soimême.connexions = {}

    async def rechercher(soimême, id_, taille, ws):
        soimême.connexions[id_] = ws
        await envoyer_message_à_ws({
            "type": "suivre",
            "id": id_,
            "données": list(range(taille))
        }, ws)

    def oublier(soimême, id_):
        soimême.connexions.pop(id_)

    async def changerTaille(soimême, id_: str, taille: int):
        if id_ not in soimême.connexions:
            return  # Si déjà annulé
        ws = soimême.connexions[id_]
        await envoyer_message_à_ws({
            "type": "suivre",
            "id": id_,
            "données": list(range(taille))
        }, ws)

    def __contains__(soimême, item):
        return item in soimême.connexions


suiveur = Suiveur()
chercheur = Chercheur()


async def traiter_message(message, ws: WebSocketConnection):
    message = json.loads(message)
    type_ = message["type"]

    if type_ == "suivre":
        fonction = tuple(message["fonction"])
        if fonction == ("fonctionSuivi",):
            await envoyer_message_à_ws({
                "type": "suivrePrêt",
                "id": message["id"]
            }, ws)
            await suiveur.suivre(message["id"], ws)
        elif fonction == ("fonctionRecherche",):
            await envoyer_message_à_ws({
                "type": "suivrePrêt",
                "id": message["id"],
                "fonctions": ["fChangerN"]
            }, ws)
            await chercheur.rechercher(message["id"], taille=message["args"]["nRésultatsDésirés"], ws=ws)
        else:
            await envoyer_message_à_ws(erreur_fonction_non_définie(message), ws)

    elif type_ == "retour":
        id_ = message["id"]
        fonction = message["fonction"]
        if fonction == "fChangerN":
            await chercheur.changerTaille(id_, taille=message["args"][0])

    elif type_ == "oublier":
        id_ = message["id"]
        if id_ in suiveur:
            suiveur.oublier(id_)
        elif id_ in chercheur:
            chercheur.oublier(id_)
        else:
            raise ValueError(id_ + " n'est pas suivi.")

    elif type_ == "action":
        fonction = tuple(message["fonction"])
        if fonction == ("obtIdDispositif",):
            résultat = "1234567890"
            await envoyer_message_à_ws({
                "type": "action",
                "id": message["id"],
                "résultat": résultat,
            }, ws)
        elif fonction == ("ceciEstUnTest", "deSousModule"):
            résultat = "C'est beau"
            await envoyer_message_à_ws({
                "type": "action",
                "id": message["id"],
                "résultat": résultat,
            }, ws)
        elif fonction == ("changerValeurSuivie",):
            await suiveur.changerValeur(message["args"]["x"])
            await envoyer_message_à_ws({
                "type": "action",
                "id": message["id"],
            }, ws)
        else:
            await envoyer_message_à_ws(erreur_fonction_non_définie(message), ws)

    else:
        raise {
            "type": "action",
            "id": message["id"] if "id" in message else None,
            "résultat": f"Type `{type_}` inconnu.",
        }


async def serveur(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            await traiter_message(message, ws)
        except ConnectionClosed:
            break


def écrire_à_stdout(*message: str):
    print(*message)
    sys.stdout.flush()


@click.group(cls=DefaultGroup, default="lancer", default_if_no_args=True)
def cli():
    pass


@click.command()
def v_constl():
    écrire_à_stdout(V_IPA_NÉCESSAIRE.strip("^"))


@click.command()
def v_constl_obli():
    écrire_à_stdout(V_IPA_NÉCESSAIRE)


@click.command()
def version():
    écrire_à_stdout(V_SERVEUR_NÉCESSAIRE.strip("^"))
    return


@click.command()
@click.option("-p", '--port', default=None)
@click.option("-m", is_flag=True, default=False)
def lancer(port, m):
    async def main():
        port_ = port or 5000

        async with trio.open_nursery() as pouponnière:
            async def _lancer_port_ws(p):
                await pouponnière.start(serve_websocket, serveur, 'localhost', int(p), None)

            if port:
                try:
                    await _lancer_port_ws(port_)
                except Exception as e:
                    écrire_à_stdout(str(e))
                    raise e

            else:
                while True:
                    try:
                        await _lancer_port_ws(port_)
                        break
                    except OSError as e:
                        messages_possibles = ["Only one usage", "Address already in use"]
                        if any(message in e.args[1] for message in messages_possibles):
                            port_ += 1
                        else:
                            écrire_à_stdout(str(e))
                            raise e

            if m:
                écrire_à_stdout("MESSAGE MACHINE : {\"type\": \"NŒUD PRÊT\", \"port\": " + str(port_) + "}")
            else:
                écrire_à_stdout(f"Serveur prêt sur port : {port_}")

    trio.run(main)


cli.add_command(v_constl)
cli.add_command(v_constl_obli)
cli.add_command(version)
cli.add_command(lancer)

if __name__ == '__main__':
    cli()
