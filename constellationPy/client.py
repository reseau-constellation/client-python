from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Optional, List, Any, Callable, Dict, Union, Tuple
from uuid import uuid4

import trio
import trio_websocket as tw

from .serveur import obtenir_contexte
from .utils import à_chameau, une_fois


# Idée de https://stackoverflow.com/questions/48282841/in-trio-how-can-i-have-a-background-task-that-lives-as-long-as-my-object-does
@asynccontextmanager
async def ouvrir_client(port: Optional[int] = None):
    async with trio.open_nursery() as pouponnière:
        async with Client(pouponnière, port) as client:
            await client.connecter()
            yield client
            print("On a terminé")


ErreurClientNonInitialisé = trio.ClosedResourceError(
    "Vous devez appeler `Client` ainsi:"
    "\n"
    "\nasync with trio.open_nursery() as pouponnière:"
    "\n\tasync with Client(pouponnière) as client:"
    "\n\t\tawait client.connecter()"
    "\n\t\tclient.faire_quelque_chose()  # par exemple"
    "\n\t\t..."
)


class Client(trio.abc.AsyncResource):
    def __init__(
            soimême,
            pouponnière,
            port: Optional[int] = None,
            _client_original: Optional[Client] = None,
            _liste_atributs: Optional[List[str]] = None
    ):
        soimême.pouponnière = pouponnière
        soimême._client_original = _client_original or soimême
        soimême._port = port

        soimême._connexion: Optional[tw.WebSocketConnection] = None
        soimême._canaux: Optional[Tuple[trio.MemorySendChannel, trio.MemoryReceiveChannel]] = None
        soimême._canal_erreurs: Optional[trio.MemorySendChannel] = None
        soimême._messages_en_attente: List[Dict] = []
        soimême._ipa_prêt = False
        soimême._liste_atributs = _liste_atributs or []
        soimême._context_annuler_écoute: Optional[trio.CancelScope] = None

        soimême.erreurs: List[str] = []

    @property
    def port(soimême) -> int:

        # trouver le port
        port = soimême._port or soimême._client_original._port or obtenir_contexte()

        if port is None:
            raise ValueError(
                "Vous devez ou bien lancer `Client` de l'intérieur d'un bloc `with Serveur()...`, "
                "ou bien spécifier le numéro de port lors de son instantiation : `Client(port=5123)`."
            )
        return port

    @property
    def connexion(soimême) -> tw.WebSocketConnection:
        connexion = soimême._client_original._connexion
        if not connexion:
            raise ErreurClientNonInitialisé
        return connexion

    @connexion.setter
    def connexion(soimême, val):
        soimême._client_original._connexion = val

    @property
    def canaux(soimême) -> Tuple[trio.MemorySendChannel, trio.MemoryReceiveChannel]:
        canaux = soimême._client_original._canaux
        if not canaux:
            raise ErreurClientNonInitialisé
        return canaux

    @canaux.setter
    def canaux(soimême, val):
        soimême._client_original._canaux = val

    @property
    def canal_envoie(soimême) -> trio.MemorySendChannel:
        return soimême.canaux[0]

    @property
    def canal_réception(soimême) -> trio.MemoryReceiveChannel:
        return soimême.canaux[1]

    @property
    def canal_erreurs(soimême) -> trio.MemorySendChannel:
        return soimême._client_original._canal_erreurs

    async def connecter(soimême, canal_erreurs: Optional[trio.MemorySendChannel] = None):
        # établir le canal pour les erreurs éventuelles
        soimême._canal_erreurs = canal_erreurs

        # établir la connexion
        url = f"ws://localhost:{soimême.port}"
        soimême.connexion = await tw.connect_websocket_url(soimême.pouponnière, url)

        # démarrer l'écoute
        soimême.canaux = trio.open_memory_channel(0)
        soimême._context_annuler_écoute = await soimême.pouponnière.start(soimême._écouter)

        message_init = {"type": "init"}
        soimême.pouponnière.start_soon(soimême._envoyer_au_port, message_init)

    async def aclose(soimême):
        print("On ferme tout")
        if soimême is not soimême._client_original:
            return

        if soimême._context_annuler_écoute:
            soimême._context_annuler_écoute.cancel()

        if soimême._connexion:
            await soimême._connexion.aclose()
            soimême._connexion = None

    async def _écouter(soimême, task_status=trio.TASK_STATUS_IGNORED):
        with trio.CancelScope() as _context:
            task_status.started(_context)
            async with soimême.canal_envoie as canal_envoie:
                while True:
                    try:
                        message = await soimême.connexion.get_message()
                    except tw.ConnectionClosed:
                        break
                    m_json = json.loads(message)
                    print("Message reçu : ", m_json)
                    type_ = m_json["type"]

                    if type_ == "prêt":
                        await soimême._ipa_activée()

                    elif type_ == "suivre":
                        m = {"id": m_json["id"], "résultat": m_json["données"]}
                        await canal_envoie.send(json.dumps(m))

                    elif type_ == "suivrePrêt":
                        m = {"id": m_json["id"]}
                        await canal_envoie.send(json.dumps(m))

                    elif type_ == "action":
                        await canal_envoie.send(json.dumps(m_json))

                    elif type_ == "erreur":
                        await canal_envoie.send(json.dumps(m_json))
                        # On rapporte ici uniquement les erreurs génériques (non spécifiques à une requète)
                        if m_json["id"] and soimême.canal_erreurs:
                            m = {"erreur": m_json["erreur"]}
                            print("erreure envoyée : ", m)
                            await soimême.canal_erreurs.send(json.dumps(m))

                        soimême._erreur(m_json["erreur"])

                    else:
                        soimême._erreur(f"Type inconnu {type_} dans message {m_json}")

    def _erreur(soimême, e: str) -> None:
        print("erreur reçue : ", e)
        soimême.erreurs.insert(0, e)

        # On envoie les erreurs au canal s'il existe. Sinon, on arrête l'exécution.
        if not soimême.canal_erreurs:
            if isinstance(e, str) and e.endswith("non définie"):
                raise AttributeError(e)
            else:
                raise RuntimeError(e)

    async def _envoyer_message(soimême, message: Dict) -> None:
        print("envoyer message")
        if soimême._client_original._ipa_prêt:
            print("le client était prêt")
            await soimême._envoyer_au_port(message)
        else:
            print("on attendra que le client soit prêt")
            soimême._client_original._messages_en_attente.append(message)

    async def _envoyer_au_port(soimême, message: Dict):
        print("message pour le port", message)
        await soimême.connexion.send_message(json.dumps(message))
        print("message envoyé au port")

    async def _ipa_activée(soimême) -> None:
        print("IPA activée")
        # Sauter cette fonction pour tous sauf le client de base
        if soimême is not soimême._client_original:
            return

        for m in soimême._messages_en_attente:
            await soimême._envoyer_au_port(m)

        soimême._messages_en_attente = []
        soimême._ipa_prêt = True

    async def _appeler_fonction_action(
            soimême,
            id_: str,
            adresse_fonction: List[str],
            liste_args: List[Any]
    ) -> Any:
        message = {
            "type": "action",
            "id": id_,
            "fonction": adresse_fonction,
            "args": liste_args,
        }
        await soimême._envoyer_message(message)
        print("On attend le résultat de : ", message)
        val = await soimême._attendre_message(id_, soimême.canal_réception.clone())
        if not val:
            soimême._erreur(
                "Le serveur local Constellation semble être en grève. \n"
                "Si les négotiations n'aboutissent pas, n'hésitez pas à "
                "nous demander de l'aide :\n"
                "https://github.com/reseau-constellation/serveur-ws/issues"
            )

        if val["type"] == "action":
            return val["résultat"]

    async def _appeler_fonction_suivre(
            soimême,
            id_: str,
            adresse_fonction: List[str],
            liste_args: List[any],
            i_arg_fonction: int
    ) -> Callable[[], None]:

        f = liste_args[i_arg_fonction]
        args_ = [a for a in liste_args if not callable(a)]
        if len(args_) != len(liste_args) - 1:
            soimême._erreur("Plus d'un argument est une fonction.")
            return lambda: None

        message = {
            "type": "suivre",
            "id": id_,
            "fonction": adresse_fonction,
            "args": args_,
            "iArgFonction": i_arg_fonction
        }

        # https://stackoverflow.com/questions/60674136/python-how-to-cancel-a-specific-task-spawned-by-a-nursery-in-python-trio
        # https://trio.readthedocs.io/en/stable/reference-core.html#trio.CancelScope
        async def _suiveur(canal, task_status=trio.TASK_STATUS_IGNORED):
            with trio.CancelScope() as _context:
                task_status.started(_context)
                async with canal:
                    async for val in canal:
                        val = json.loads(val)
                        print("val", val)
                        if val["id"] == id_:
                            await f(val["résultat"])

        context = await soimême.pouponnière.start(_suiveur, soimême.canal_réception.clone())

        await soimême._envoyer_message(message)

        def f_oublier():
            message_oublier = {
                "type": "oublier",
                "id": id_,
            }
            soimême.pouponnière.start_soon(soimême._envoyer_message(message_oublier))
            context.cancel()

        await soimême._attendre_message(id_, soimême.canal_réception.clone())
        return f_oublier

    async def _attendre_message(soimême, id_: str, canal_réception):
        print("On attend le message : ", id_)
        async with canal_réception:
            async for val in canal_réception:
                message = json.loads(val)
                print("On a reçu un message : ", message)
                if message["id"] == id_:
                    if message["type"] == "erreur":
                        soimême._erreur(message["erreur"])
                    return message

    async def obt_données_tableau(soimême, id_tableau: str):
        async def f_async(f):
            return await soimême.tableaux.suivre_données(id_tableau, f)

        return await une_fois(f_async, soimême.pouponnière)

    async def obt_données_réseau(soimême, motclef_unique: str, nom_unique_tableau: str):
        async def f_async(f):
            return await soimême.réseau.suivre_données(motclef_unique, nom_unique_tableau, f)

        return await une_fois(f_async, soimême.pouponnière)

    async def __call__(
            soimême,
            *args: Any
    ) -> Union[Any, Callable[[], None]]:

        id_ = str(uuid4())
        liste_args = list(args)
        i_arg_fonction = next((i for i, é in enumerate(liste_args) if callable(é)), None)

        if i_arg_fonction is not None:
            return await soimême._appeler_fonction_suivre(
                id_, adresse_fonction=soimême._liste_atributs, liste_args=liste_args, i_arg_fonction=i_arg_fonction
            )
        else:
            return await soimême._appeler_fonction_action(
                id_, adresse_fonction=soimême._liste_atributs, liste_args=liste_args
            )

    def __getattr__(soimême, item):
        return Client(
            soimême.pouponnière,
            _client_original=soimême._client_original,
            _liste_atributs=soimême._liste_atributs + [à_chameau(item)]
        )
