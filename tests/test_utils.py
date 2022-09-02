from unittest import TestCase

import pandas as pd
import trio
import pandas.testing as pdt

from constellationPy.utils import à_chameau, à_kebab, une_fois, tableau_à_pandas, pandas_à_constellation


class TestUtils(TestCase):
    def test_à_chameau(soimême):
        chameau = à_chameau("suivre_données_tableau")
        soimême.assertEqual(chameau, "suivreDonnéesTableau")

    def test_à_kebab(soimême):
        kebab = à_kebab("suivreDonnéesTableau")
        soimême.assertEqual(kebab, "suivre_données_tableau")

    async def test_une_fois(soimême):
        async with trio.open_nursery() as pouponnière:
            async def f_async(f, task_status=trio.TASK_STATUS_IGNORED):
                with trio.CancelScope() as _context:
                    task_status.started(_context)
                    await f(1)
                    await f(2)

            x = await une_fois(f_async, pouponnière)
        soimême.assertEqual(x, 1)

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
