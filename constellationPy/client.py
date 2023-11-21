from __future__ import annotations

import inspect
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Any, Callable, Dict, Union, Tuple, Awaitable
from uuid import uuid4

import pandas as pd
import trio
import trio_websocket as tw

from .const import LIEN_SIGNALEMENT_ERREURS
from .serveur import obtenir_contexte
from .utils import à_chameau, à_kebab, fais_rien_asynchrone, une_fois, tableau_exporté_à_pandas, attendre_stabilité


# Idée de https://stackoverflow.com/questions/48282841/in-trio-how-can-i-have-a-background-task-that-lives-as-long-as-my-object-does
@asynccontextmanager
async def ouvrir_client(port: Optional[int] = None) -> Client:
    async with trio.open_nursery() as pouponnière:
        async with Client(pouponnière, port) as client:
            await client.connecter()
            yield client


ErreurClientNonInitialisé = trio.ClosedResourceError(
    "Tout appel à un instance de `Client` doit avoir lieu dans un bloque de context ainsi :"
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
            pouponnière: trio.Nursery,
            port: Optional[int] = None,
            _client_original: Optional[Client] = None,
            _liste_attributs: Optional[List[str]] = None
    ):
        soimême.pouponnière = pouponnière
        soimême._client_original = _client_original or soimême
        soimême._port = port

        soimême._connexion: Optional[tw.WebSocketConnection] = None
        soimême._canaux: Optional[Tuple[trio.MemorySendChannel, trio.MemoryReceiveChannel]] = None
        soimême._canal_erreurs: Optional[trio.MemorySendChannel] = None
        soimême._liste_attributs = _liste_attributs or []
        soimême._context_annuler_écoute: Optional[trio.CancelScope] = None
        soimême._écouteurs = {}

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
    def écouteurs(soimême):
        return soimême._client_original._écouteurs

    @écouteurs.setter
    def écouteurs(soimême, val):
        soimême._client_original._écouteurs = val

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
        soimême._context_annuler_écoute = await soimême.pouponnière.start(soimême._écouter)

    async def aclose(soimême):
        if soimême is not soimême._client_original:
            return

        if soimême._context_annuler_écoute:
            soimême._context_annuler_écoute.cancel()

        if soimême._connexion:
            await soimême._connexion.aclose()
            soimême._connexion = None

        soimême.écouteurs = {}

    def _enregistrer_écouteur(soimême, id_: str, f):
        soimême.écouteurs[id_] = f

    def _effacer_écouteur(soimême, id_: str):
        soimême.écouteurs.pop(id_)

    async def _écouter(soimême, task_status=trio.TASK_STATUS_IGNORED):
        with trio.CancelScope() as _context:
            task_status.started(_context)
            while True:
                try:
                    message = await soimême.connexion.get_message()
                except tw.ConnectionClosed:
                    break
                logging.debug("Message ws reçu : " + json.dumps(json.loads(message), ensure_ascii=False))
                m_json = json.loads(message)
                type_ = m_json["type"]

                if "id" in m_json and m_json["id"] in soimême.écouteurs:
                    await soimême.écouteurs[m_json["id"]](m_json)

                if type_ == "erreur":
                    # On rapporte ici uniquement les erreurs génériques (non spécifiques à une requête)
                    if "id" in m_json and soimême.canal_erreurs:
                        m = {"erreur": m_json["erreur"]}
                        await soimême.canal_erreurs.send(json.dumps(m))

                    soimême._erreur(m_json["erreur"])

    def _erreur(soimême, e: str) -> None:
        soimême.erreurs.insert(0, e)

        # On envoie les erreurs au canal s'il existe. Sinon, on arrête l'exécution.
        if not soimême.canal_erreurs:
            if isinstance(e, str) and "n'existe pas" in e:
                raise AttributeError(e)
            else:
                raise RuntimeError(e)

    async def _envoyer_message(soimême, message: Dict) -> None:
        logging.debug("Message envoyé, " + json.dumps(message, ensure_ascii=False))
        await soimême.connexion.send_message(json.dumps(message, ensure_ascii=False))

    async def _appeler_fonction_action(
            soimême,
            id_: str,
            adresse_fonction: List[str],
            args: Dict[str, Any]
    ) -> Any:
        message = {
            "type": "action",
            "id": id_,
            "fonction": adresse_fonction,
            "args": args,
        }

        retour = {
            "prêt": trio.Event(),
            "val": None
        }

        async def f_suivi(v):
            if v["type"] == "action":
                retour["val"] = v["résultat"] if "résultat" in v else None
                retour["prêt"].set()
                soimême._effacer_écouteur(id_)
            else:
                soimême._erreur(
                    "Valeur reçue : " + json.dumps(v, ensure_ascii=False, indent=2) +
                    ". Avez-vous utilisé les bons arguments pour la fonction que vous venez d'appeler ?. \n"
                    "Si vous êtes sûre que oui, c'est peut-être le serveur local Constellation qui est en grève. \n"
                    "Si les négotiations n'aboutissent pas, n'hésitez pas à "
                    "nous demander d'intervenir :\n"
                    f"\t{LIEN_SIGNALEMENT_ERREURS}"
                )
                retour["val"] = None
                retour["prêt"].set()

        soimême._enregistrer_écouteur(id_, f_suivi)
        await soimême._envoyer_message(message)

        await retour["prêt"].wait()

        return retour["val"]

    async def _appeler_fonction_suivre(
            soimême,
            id_: str,
            adresse_fonction: List[str],
            args: Dict[str, any],
            nom_arg_fonction: str
    ) -> Union[Callable[[], Awaitable[None]], Dict[str, Callable[[Any], Awaitable[None]]]]:

        f = args.pop(nom_arg_fonction)
        args = {c: v for c, v in args.items() if not callable(v)}
        if any(callable(v) for v in args.values()):
            soimême._erreur("Plus d'un argument est une fonction.")
            return fais_rien_asynchrone

        message = {
            "type": "suivre",
            "id": id_,
            "fonction": adresse_fonction,
            "args": args,
            "nomArgFonction": nom_arg_fonction
        }

        retour = {
            "prêt": trio.Event(),
            "statut": None
        }

        async def f_suivi(val):
            if val["type"] == "suivrePrêt":
                retour["statut"] = val
                retour["prêt"].set()
            elif val["type"] == "suivre":
                if inspect.iscoroutinefunction(f):
                    soimême.pouponnière.start_soon(f, val["données"])
                else:
                    f(val["données"])

        soimême._enregistrer_écouteur(id_, f_suivi)
        await soimême._envoyer_message(message)

        async def f_oublier():
            message_oublier = {
                "type": "retour",
                "id": id_,
                "fonction": "fOublier"
            }
            await soimême._envoyer_message(message_oublier)
            soimême._effacer_écouteur(id_)

        await retour["prêt"].wait()

        valeur_retour = retour["statut"]

        def générer_f_retour(nom: str):
            async def f_retour(*args_):
                message_retour = {
                    "type": "retour",
                    "id": id_,
                    "fonction": nom,
                    "args": args_
                }
                await soimême._envoyer_message(message_retour)

            return f_retour

        if "fonctions" in valeur_retour and valeur_retour["fonctions"]:
            return {
                "fOublier": f_oublier,
                **{fn: générer_f_retour(fn) for fn in valeur_retour["fonctions"]}
            }
        return f_oublier

    async def obt_données_tableau(
            soimême,
            id_tableau: str,
            langues: Optional[str | list[str]] = None,
            formatDonnées="pandas",
            patience: int | float=1
    ):
        async def f_suivi(f):
            return await soimême.tableaux.suivre_données_exportation(id_tableau=id_tableau, f=f, langues=langues)

        données = await une_fois(f_suivi, soimême.pouponnière, attendre_stabilité(patience))

        if formatDonnées.lower() == "pandas":
            return tableau_exporté_à_pandas(données)
        elif formatDonnées.lower() == "constellation":
            return données
        else:
            raise ValueError(formatDonnées)

    async def obt_données_tableau_nuée(
            soimême, id_nuée: str, clef_tableau: str, n_résultats_désirés: int,
            langues: Optional[str | list[str]] = None, formatDonnées="pandas",
            patience: int | float=1
    ):
        async def f_suivi(f):
            return await soimême.nuées.suivre_données_exportation_tableau(
                id_nuée=id_nuée, clef_tableau=clef_tableau,
                langues=langues,
                n_résultats_désirés=n_résultats_désirés, f=f
            )

        données = await une_fois(f_suivi, soimême.pouponnière, attendre_stabilité(patience))

        if formatDonnées.lower() == "pandas":
            return tableau_exporté_à_pandas(données)
        elif formatDonnées.lower() == "constellation":
            return données
        else:
            raise ValueError(formatDonnées)

    async def __call__(
            soimême,
            **argsmc: Any
    ) -> Union[Any, Callable[[], None]]:

        id_ = str(uuid4())
        nom_arg_fonction = next((c for c, v in argsmc.items() if callable(v)), None)
        adresse_fonction = [à_chameau(x) for x in soimême._liste_attributs]
        argsmc = {à_chameau(c): v for c, v in argsmc.items()}

        if nom_arg_fonction is not None:
            return await soimême._appeler_fonction_suivre(
                id_, adresse_fonction=adresse_fonction, args=argsmc, nom_arg_fonction=nom_arg_fonction
            )
        else:
            return await soimême._appeler_fonction_action(
                id_, adresse_fonction=adresse_fonction, args=argsmc
            )

    def __getattr__(soimême, item):
        return Client(
            soimême.pouponnière,
            _client_original=soimême._client_original,
            _liste_attributs=soimême._liste_attributs + [à_kebab(item)]
        )
