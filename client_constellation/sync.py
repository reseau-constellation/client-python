from typing import Optional, List

import trio

from .client import ouvrir_client
from .utils import à_chameau


async def une_fois(f_async, pouponnière):
    canal_envoie, canal_réception = trio.open_memory_channel(0)

    async def f_réception(résultat):
        async with canal_envoie:
            await canal_envoie.send(résultat)

    pouponnière.start_soon(f_async, f_réception)
    with canal_réception:
        async for message in canal_réception:
            return message


class ClientSync:
    def __init__(soimême, port: Optional[int], _liste_atributs: Optional[List[str]] = None):
        soimême.port = port
        soimême._liste_atributs = _liste_atributs or []

    def __getattr__(soimême, item):
        return ClientSync(
            soimême.port, soimême._liste_atributs + [à_chameau(item)]
        )

    def __call__(soimême, *args):

        fonction_suivi = soimême._liste_atributs[-1].startswith("suivre")
        i_arg_fonction = next(i for i, é in enumerate(args) if callable(é))

        def f_async():
            async with ouvrir_client() as client:
                f_client = client
                for x in soimême._liste_atributs:
                    f_client = getattr(client, x)

                if fonction_suivi:
                    async def f_pour_une_fois(f):
                        liste_args = list(args)
                        liste_args[i_arg_fonction] = f
                        return await f_client(*liste_args)

                    return await une_fois(f_pour_une_fois, client.pouponnière)

                return await f_client(*args)

        return trio.run(f_async)
