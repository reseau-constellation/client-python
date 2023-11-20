from unittest import TestCase

import pandas as pd
import pandas.testing as pdt
import trio

from constellationPy.utils import à_chameau, à_kebab, une_fois_sans_oublier, tableau_à_pandas, pandas_à_constellation, \
    une_fois, attendre_stabilité


class TestUtils(TestCase):
    def test_à_chameau(soimême):
        chameau = à_chameau("suivre_données_tableau")
        soimême.assertEqual(chameau, "suivreDonnéesTableau")

    def test_à_kebab(soimême):
        kebab = à_kebab("suivreDonnéesTableau")
        soimême.assertEqual(kebab, "suivre_données_tableau")

    async def test_une_fois_sans_oublier(soimême):
        async with trio.open_nursery() as pouponnière:
            async def f_async(f, task_status=trio.TASK_STATUS_IGNORED):
                with trio.CancelScope() as _context:
                    task_status.started(_context.cancel)
                    await f(1)
                    await f(2)

            x = await une_fois_sans_oublier(f_async, pouponnière)
        soimême.assertEqual(x, 1)

    async def test_une_fois_sans_oublier_avec_condition(soimême):
        async with trio.open_nursery() as pouponnière:
            async def f_async(f, task_status=trio.TASK_STATUS_IGNORED):
                with trio.CancelScope() as _context:
                    task_status.started(_context.cancel)
                    await f(1)
                    await f(2)

            async def condition(val):
                return val > 1

            x = await une_fois_sans_oublier(f_async, pouponnière, condition)
        soimême.assertEqual(x, 2)

    async def test_une_fois(soimême):
        oubl = {"ié": False}
        async with trio.open_nursery() as pouponnière:
            async def f_suivi(f):
                async def f_oublier():
                    oubl["ié"] = True

                pouponnière.start_soon(f, 123)
                return f_oublier

            x = await une_fois(f_suivi, pouponnière=pouponnière)

        soimême.assertEqual(x, 123)
        soimême.assertTrue(oubl["ié"])

    async def test_une_fois_avec_condition(soimême):
        oubl = {"ié": False}
        async with trio.open_nursery() as pouponnière:
            async def f_suivi(f):
                async def f_oublier():
                    oubl["ié"] = True

                pouponnière.start_soon(f, 123)
                pouponnière.start_soon(f, 456)
                return f_oublier

            async def condition(val):
                return val > 150

            x = await une_fois(f_suivi, pouponnière=pouponnière, fCond=condition)

        soimême.assertEqual(x, 456)
        soimême.assertTrue(oubl["ié"])

    async def test_attendre_stabilité(soimême):
        vals = {}
        attendre_stable = attendre_stabilité(0.1)
        async def f(x: str):
            vals[x] = await attendre_stable(x)

        async with trio.open_nursery() as pouponnière:
            pouponnière.start_soon(f, "a")
            await trio.sleep(0.05)
            pouponnière.start_soon(f, "b")

        soimême.assertFalse(vals["a"])
        soimême.assertTrue(vals["b"])

    def test_tableau_à_pandas(soimême):
        tableau = [{"empreinte": "abc", "données": {"a": 1, "b": 2}}, {"empreinte": "def", "données": {"a": 3}}]
        données_pandas = tableau_à_pandas(tableau)
        pdt.assert_frame_equal(données_pandas, pd.DataFrame({"a": [1, 3], "b": [2, None]}))

    def test_tableau_à_pandas_index(soimême):
        tableau = [{"empreinte": "abc", "données": {"a": 1, "b": 2}}, {"empreinte": "def", "données": {"a": 3}}]
        données_pandas_index = tableau_à_pandas(tableau, index_empreinte=True)
        pdt.assert_frame_equal(données_pandas_index, pd.DataFrame({"a": [1, 3], "b": [2, None]}, index=["abc", "def"]))

    def test_pandas_à_constellation(soimême):
        données_pandas = pd.DataFrame({"a": [1, 3], "b": [2, None]})
        données_constellation = pandas_à_constellation(données_pandas)

        référence = [{"a": 1, "b": 2}, {"a": 3}]

        soimême.assertListEqual(données_constellation, référence)
