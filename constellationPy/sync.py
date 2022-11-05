from typing import Optional, List

import trio

from .client import ouvrir_client
from .utils import à_kebab, une_fois


class ClientSync(object):
    def __init__(soimême, port: Optional[int] = None, _liste_attributs: Optional[List[str]] = None):
        soimême.port = port
        soimême._liste_attributs = _liste_attributs or []

    def __getattr__(soimême, item):
        return ClientSync(soimême.port, soimême._liste_attributs + [à_kebab(item)])

    def __call__(soimême, **argsmc):
        nom_arg_fonction = next((c for c, v in argsmc.items() if callable(v)), None)
        argsmc = {c: v for c, v in argsmc.items()}  # Ne pas convertir à chameau ici ; le client asynchrone s'en occupe

        async def f_async():
            async with ouvrir_client() as client:
                f_client = client
                for x in soimême._liste_attributs:
                    f_client = getattr(f_client, x)

                if nom_arg_fonction:
                    async def f_pour_une_fois(f):
                        argsmc[nom_arg_fonction] = f
                        return await f_client(**argsmc)

                    return await une_fois(f_pour_une_fois, client.pouponnière)

                return await f_client(**argsmc)

        return trio.run(f_async)
