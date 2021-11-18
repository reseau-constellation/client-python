from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

import trio

if TYPE_CHECKING:
    pass


def à_chameau(text: str) -> str:
    # https://stackoverflow.com/questions/60978672/python-string-to-camelcase
    s = text.replace("-", " ").replace("_", " ")
    s = s.split()
    if len(text) == 0:
        return text
    return s[0] + ''.join(i.capitalize() for i in s[1:])


def fais_rien() -> None:
    pass


async def une_fois(f_suivre, pouponnière: trio.Nursery) -> Any:
    canal_envoie, canal_réception = trio.open_memory_channel(0)

    async def f_réception(résultat):
        async with canal_envoie:
            await canal_envoie.send(résultat)

    f_oublier = (await pouponnière.start(f_suivre, f_réception)).cancel

    async with canal_réception:
        async for message in canal_réception:
            f_oublier()
            return message
