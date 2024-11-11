import io
import json
import sys

import click
import trio
from click_default_group import DefaultGroup
from trio_websocket import serve_websocket, ConnectionClosed, WebSocketConnection

try:
    from constellationPy.const import V_SERVEUR_NÉCESSAIRE
except ModuleNotFoundError:
    # Pour tests sur Ubuntu... je ne suis pas sûr pourquoi ça ne fonctionne pas...
    V_SERVEUR_NÉCESSAIRE = "^2.0.6"
_données = {}

# Nécessaire pour Windows
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')


def erreur_fonction_non_définie(message):
    return {
        "type": "erreur",
        "idRequête": message["idRequête"],
        "erreur": f"Fonction `Client.{'.'.join(message['fonction'])}()` n'existe pas ou n'est pas une fonction."
    }


async def envoyer_message_à_ws(message, ws: WebSocketConnection):
    await ws.send_message(json.dumps(message))


class Suiveur(object):
    def __init__(soimême):
        soimême.connexions = {}
        soimême.valeur = None

    async def suivre(soimême, idRequête, ws):
        soimême.connexions[idRequête] = ws
        await envoyer_message_à_ws({
            "type": "suivre",
            "idRequête": idRequête,
            "données": soimême.valeur
        }, ws)

    def oublier(soimême, idRequête):
        soimême.connexions.pop(idRequête)

    async def changerValeur(soimême, val):
        soimême.valeur = val
        for idRequête, ws in soimême.connexions.items():
            await envoyer_message_à_ws({
                "type": "suivre",
                "idRequête": idRequête,
                "données": soimême.valeur
            }, ws)

    def __contains__(soimême, item):
        return item in soimême.connexions


class Chercheur(object):
    def __init__(soimême):
        soimême.connexions = {}

    async def rechercher(soimême, idRequête, taille, ws):
        soimême.connexions[idRequête] = ws
        await envoyer_message_à_ws({
            "type": "suivre",
            "idRequête": idRequête,
            "données": list(range(taille))
        }, ws)

    def oublier(soimême, idRequête):
        soimême.connexions.pop(idRequête)

    async def changerTaille(soimême, idRequête: str, taille: int):
        if idRequête not in soimême.connexions:
            return  # Si déjà annulé
        ws = soimême.connexions[idRequête]
        await envoyer_message_à_ws({
            "type": "suivre",
            "idRequête": idRequête,
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
                "idRequête": message["idRequête"]
            }, ws)
            await suiveur.suivre(message["idRequête"], ws)
        elif fonction == ("fonctionRecherche",):
            await envoyer_message_à_ws({
                "type": "suivrePrêt",
                "idRequête": message["idRequête"],
                "fonctions": ["fChangerN"]
            }, ws)
            await chercheur.rechercher(message["idRequête"], taille=message["args"]["nRésultatsDésirés"], ws=ws)
        else:
            await envoyer_message_à_ws(erreur_fonction_non_définie(message), ws)

    elif type_ == "retour":
        idRequête = message["idRequête"]
        fonction = message["fonction"]
        if fonction == "fChangerN":
            await chercheur.changerTaille(idRequête, taille=message["args"][0])

    elif type_ == "oublier":
        idRequête = message["idRequête"]
        if idRequête in suiveur:
            suiveur.oublier(idRequête)
        elif idRequête in chercheur:
            chercheur.oublier(idRequête)
        else:
            raise ValueError(idRequête + " n'est pas suivi.")

    elif type_ == "action":
        fonction = tuple(message["fonction"])
        if fonction == ("obtIdDispositif",):
            résultat = "1234567890"
            await envoyer_message_à_ws({
                "type": "action",
                "idRequête": message["idRequête"],
                "résultat": résultat,
            }, ws)
        elif fonction == ("ceciEstUnTest", "deSousModule"):
            résultat = "C'est beau"
            await envoyer_message_à_ws({
                "type": "action",
                "idRequête": message["idRequête"],
                "résultat": résultat,
            }, ws)
        elif fonction == ("changerValeurSuivie",):
            await suiveur.changerValeur(message["args"]["x"])
            await envoyer_message_à_ws({
                "type": "action",
                "idRequête": message["idRequête"],
            }, ws)
        else:
            await envoyer_message_à_ws(erreur_fonction_non_définie(message), ws)

    else:
        raise {
            "type": "action",
            "idRequête": message["idRequête"] if "idRequête" in message else None,
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
def version():
    écrire_à_stdout(V_SERVEUR_NÉCESSAIRE.strip("^"))
    return


@click.command()
@click.option("-p", '--port', default=None)
@click.option("-m", is_flag=True, default=False)
def lancer(port, m):
    async def main():
        port_ = port or 5000
        codeSecret = "voici un code pas ben ben secret"

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
                écrire_à_stdout("MESSAGE MACHINE : {\"type\": \"NŒUD PRÊT\", \"port\": " + str(port_) + ", \"codeSecret\": \"" + str(codeSecret) + "\"}")
            else:
                écrire_à_stdout(f"Serveur prêt sur port : {port_}")

    trio.run(main)

cli.add_command(version)
cli.add_command(lancer)

if __name__ == '__main__':
    cli()
