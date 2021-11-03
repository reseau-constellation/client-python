from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Optional, List, Any, Callable, Dict, Union, Tuple
from uuid import uuid4

import trio
import trio_websocket as tw

from .serveur import obtenir_context
from .utils import à_chameau


# Idée de https://stackoverflow.com/questions/48282841/in-trio-how-can-i-have-a-background-task-that-
# lives-as-long-as-my-object-does
@asynccontextmanager
async def ouvrir_client(port: Optional[int] = None):
    async with trio.open_nursery() as pouponnière:
        async with Client(pouponnière, port) as client:
            await client.connecter()
            yield client


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

        # trouver le port
        port = soimême._port or soimême._client_original._port or obtenir_context()
        if port is None:
            raise ValueError(
                "Vous devez ou bien lancer `Client` de l'intérieur d'un bloc `with Serveur()...`, "
                "ou bien spécifier le numéro de port lors de son instantiation."
            )
        url = f"ws://localhost:{port}"

        # établir la connexion
        soimême.connexion = tw.open_websocket_url(url)
        await soimême.connexion.__aenter__()

        # démarrer l'écoute
        soimême.canaux = trio.open_memory_channel(0)
        soimême._context_annuler_écoute = soimême.pouponnière.start(soimême._écouter)

        message_init = {"type": "init"}
        soimême.pouponnière.start_soon(soimême._envoyer_au_port, message_init)

    async def aclose(soimême):
        if soimême._context_annuler_écoute:
            soimême._context_annuler_écoute.cancel()

        if soimême._connexion:
            await soimême._connexion.__aexit__()
        soimême._connexion = None

    async def _écouter(soimême):
        with trio.CancelScope() as _context:
            trio.TASK_STATUS_IGNORED.started(_context)
            async with soimême.canal_envoie.clone() as canal_envoie:
                while True:
                    message = await soimême.connexion.get_message()
                    m_json = json.loads(message)
                    try:
                        type_ = m_json["type"]
                        id_ = m_json["id"]

                        if type_ == "prêt":
                            await soimême._ipa_activée()

                        elif type_ == "suivre":
                            m = {"id": id_, "résultat": m_json["données"]}
                            canal_envoie.send(m)

                        elif type_ == "suivrePrêt":
                            m = {"id": id_}
                            canal_envoie.send(json.dumps(m))

                        elif type_ == "action":
                            m = {"id": id_, "résultat": m_json["résultat"]}
                            canal_envoie.send(json.dumps(m))

                        elif type_ == "erreur":
                            await soimême._erreur(m_json["erreur"])

                        else:
                            await soimême._erreur(f"Type inconnu {type_} dans message {m_json}")

                    except Exception as e:
                        await soimême._erreur(str(e))

    async def _erreur(soimême, e: str) -> None:
        soimême.erreurs.insert(0, e)

        # On envoie les erreurs au canal s'il existe. Sinon, on arrête l'exécution.
        if soimême.canal_erreurs:
            m = {"erreur": e}
            await soimême.canal_erreurs.send(json.dumps(m))
        else:
            raise RuntimeError(e)

    async def _envoyer_message(soimême, message: Dict) -> None:
        if soimême._client_original._ipa_prêt:
            await soimême._envoyer_au_port(message)
        else:
            soimême._client_original._messages_en_attente.append(message)

    async def _envoyer_au_port(soimême, message: Dict):
        await soimême.connexion.send_message(json.dumps(message))

    async def _ipa_activée(soimême) -> None:

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
        val = await soimême._attendre_message(id_)

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
            await soimême._erreur("Plus d'un argument est une fonction.")
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
        async def _suiveur(canal):
            with trio.CancelScope() as _context:
                trio.TASK_STATUS_IGNORED.started(_context)
                async with canal:
                    async for val in canal:
                        if val["id"] == id_:
                            await f(val["résultat"])

        context = soimême.pouponnière.start(_suiveur, soimême.canal_réception.clone())

        await soimême._envoyer_message(message)

        def f_oublier():
            message_oublier = {
                "type": "oublier",
                "id": id_,
            }
            soimême.pouponnière.start_soon(soimême._envoyer_message(message_oublier))
            context.cancel()

        await soimême._attendre_message(id_)
        return f_oublier

    async def _attendre_message(soimême, id_: str):
        async with soimême.canal_réception.clone() as canal_réception:
            async for val in canal_réception:
                if val["id"] == id_:
                    return val

    async def __call__(
            soimême,
            *args: Any
    ) -> Union[Any, Callable[[], None]]:

        id_ = str(uuid4())
        liste_args = list(args)
        i_arg_fonction = next(i for i, é in enumerate(liste_args) if callable(é))

        if i_arg_fonction:
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
            _client_original=soimême,
            _liste_atributs=soimême._liste_atributs + [à_chameau(item)]
        )
