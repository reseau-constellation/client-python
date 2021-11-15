from __future__ import annotations

from typing import Any, Union
from typing import TYPE_CHECKING

import trio

if TYPE_CHECKING:
    from constellationPy import Client


def à_chameau(text: str) -> str:
    # https://stackoverflow.com/questions/60978672/python-string-to-camelcase
    s = text.replace("-", " ").replace("_", " ")
    s = s.split()
    if len(text) == 0:
        return text
    return s[0] + ''.join(i.capitalize() for i in s[1:])


def fais_rien() -> None:
    pass


async def une_fois(f_async, pouponnière: Union[trio.Nursery, Client]) -> Any:
    if isinstance(pouponnière, Client):
        pouponnière = Client.pouponnière
    canal_envoie, canal_réception = trio.open_memory_channel(0)

    async def f_réception(résultat):
        async with canal_envoie:
            await canal_envoie.send(résultat)

    pouponnière.start_soon(f_async, f_réception)
    with canal_réception:
        async for message in canal_réception:
            return message
