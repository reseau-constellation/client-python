import json
import sys
import uuid

import click
import trio
from click_default_group import DefaultGroup
from trio_websocket import serve_websocket, ConnectionClosed

try:
    from constellationPy.const import V_SERVEUR_NÉCESSAIRE
except ModuleNotFoundError:
    # Pour tests sur Ubuntu... pas sûr pourquoi ça ne fonctionne pas...
    V_SERVEUR_NÉCESSAIRE = "^0.1.0"

_données = {}


def erreur_fonction_non_définie(message):
    return {
        "type": "erreur",
        "id": message["id"],
        "erreur": f"Fonction `Client.{'.'.join(message['fonction'])}()` non définie"
    }


async def traiter_message(message):
    message = json.loads(message)
    type_ = message["type"]

    if type_ == "init":
        return {
            "type": "prêt"
        }
    elif type_ == "suivre":
        fonction = tuple(message["fonction"])
        if fonction == ("tableaux", "suivreDonnées"):
            async def f(canal_envoyer, task_status=trio.TASK_STATUS_IGNORED):
                with trio.CancelScope() as _context:
                    task_status.started(_context)
                    async with canal_envoyer:
                        await canal_envoyer
            # annuler = pouponnière.start(f, canal_envoyer)
        else:
            return erreur_fonction_non_définie(message)
        return {
            "type": "suivrePrêt",
            "id": message["id"]
        }
    elif type_ == "oublier":
        id_ = message["id"]
        # if id_ in fonctions_oublier:
        #     f = fonctions_oublier.pop(id_)
        #     f()
    elif type_ == "action":
        fonction = tuple(message["fonction"])
        if fonction == ("obtIdOrbite",):
            résultat = "1234567890"
        elif fonction == ("ceciEstUnTest", "deSousModule"):
            résultat = "C'est beau"
        elif fonction == ("bds", "créerBd") \
                or fonction == ("bds", "ajouterTableauBd") \
                or fonction == ("variables", "créerVariable"):
            résultat = "orbitdb/zdpu..." + str(uuid.uuid4())
        elif fonction == ("tableaux", "ajouterColonneTableau"):
            résultat = str(uuid.uuid4())
        elif fonction == ("tableaux", "ajouterÉlément"):
            id_tableau, élément = message["args"]
            élément["id"] = str(uuid.uuid4())
            if id_tableau not in _données:
                _données[id_tableau] = []
            _données[id_tableau] += [élément]
            résultat = élément["id"]
        else:
            return erreur_fonction_non_définie(message)
        return {
            "type": "action",
            "id": message["id"],
            "résultat": résultat,
        }
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
            réponse = await traiter_message(message)
            await ws.send_message(json.dumps(réponse))
        except ConnectionClosed:
            break


def écrire_à_stdout(*message: str):
    print(*message)
    sys.stdout.flush()


@click.group(cls=DefaultGroup, default='lancer', default_if_no_args=True)
def cli():
    pass


@cli.command("v-constl")
def v_constl():
    écrire_à_stdout("1.0.1")


@cli.command("v-constl-obli")
def v_constl():
    écrire_à_stdout("^1.0.0")


@cli.command("lancer")
@click.option("-p", '--port', default=None)
@click.option("-v", '--version/--sans-version', default=False)
def lancer(port, version):
    if version:
        écrire_à_stdout(V_SERVEUR_NÉCESSAIRE.strip("^"))
        return

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


if __name__ == '__main__':
    cli()
