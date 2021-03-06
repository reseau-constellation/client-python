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

    def __call__(soimême, *args):
        print(soimême._liste_attributs)
        fonction_suivi = soimême._liste_attributs[-1].startswith("suivre")

        async def f_async():
            async with ouvrir_client() as client:
                f_client = client
                for x in soimême._liste_attributs:
                    f_client = getattr(f_client, x)

                if fonction_suivi:
                    i_arg_fonction = next(i for i, é in enumerate(args) if callable(é))

                    async def f_pour_une_fois(f):
                        liste_args = list(args)
                        liste_args[i_arg_fonction] = f
                        return await f_client(*liste_args)

                    return await une_fois(f_pour_une_fois, client.pouponnière)

                return await f_client(*args)

        return trio.run(f_async)
