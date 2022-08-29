from unittest import TestCase

import trio

from constellationPy.utils import à_chameau, à_kebab, une_fois


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
