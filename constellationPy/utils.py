from __future__ import annotations

import inspect
from typing import Any, TypedDict, Dict, List, Callable, Coroutine
from typing import TYPE_CHECKING

import pandas as pd
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


def à_kebab(text: str) -> str:
    return ''.join(['_' + x.lower() if x.isupper() else x for x in text]).lstrip('_')


def fais_rien() -> None:
    pass


async def fais_rien_asynchrone() -> None:
    pass


async def une_fois_sans_oublier(
        f_suivre: Callable[[Callable[[Any, str], None]], Coroutine],
        pouponnière: trio.Nursery
) -> Any:
    canal_envoie, canal_réception = trio.open_memory_channel(0)

    async def f_réception(résultat):
        async with canal_envoie:
            await canal_envoie.send(résultat)

    f_oublier = await pouponnière.start(f_suivre, f_réception)

    async with canal_réception:
        async for message in canal_réception:
            if inspect.iscoroutinefunction(f_oublier):
                await f_oublier()
            else:
                f_oublier()
            return message


async def une_fois(
        f_suivi: Callable[[Callable[[Any], None]], Coroutine[None, None]],
        pouponnière: trio.Nursery
) -> Any:
    async def f_async(f, task_status=trio.TASK_STATUS_IGNORED):
        with trio.CancelScope() as _context:
            f_oublier = await f_suivi(f)

            async def annuler():
                await f_oublier()
                _context.cancel()

            task_status.started(annuler)

    return await une_fois_sans_oublier(f_async, pouponnière)


type_élément = TypedDict("type_élément", {"empreinte": str, "données": Dict[str, Any]})
type_tableau = List[type_élément]


def tableau_à_pandas(tableau: type_tableau, index_empreinte=False) -> pd.DataFrame:
    index = [x["empreinte"] for x in tableau] if index_empreinte else None
    données = [x["données"] for x in tableau]

    données_pandas = pd.DataFrame(données, index=index)
    return données_pandas


def pandas_à_constellation(données_pandas: pd.DataFrame) -> List[Dict[str, Any]]:
    données = []
    for _, r in données_pandas.iterrows():
        r_finale = {c: v for c, v in r.to_dict().items() if not pd.isna(v)}
        données.append(r_finale)

    return données
