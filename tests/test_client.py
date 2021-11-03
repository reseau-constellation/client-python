from unittest import TestCase

from client_constellation.client import ouvrir_client
from .ressources.faux_serveur import Serveur


class TestClient(TestCase):

    async def test_serveur(soimême):
        with Serveur():
            async with ouvrir_client() as client:
                client.tableaux.suivreDonnées()

class Test(TestCase):

    async def setUp(soimême) -> None:
        soimême.client = Client()
        await soimême.client.__aenter__()

    async def test_functionality(soimême):
        données = await soimême.client.obt_données_tableau("orbitdb/...")
        soimême.assertEqual(expected, result)

    async def test_functionality2(soimême):
        données = await soimême.client.obt_données_réseau("clef unique bd", "clef unique tableau")
        soimême.assertEqual(expected, result)

    async def test_functionality3(soimême):
        données = await une_fois(lambda x: soimême.client.tableaux.suivre_données("orbitdb/...", x))
        données2 = await une_fois(lambda x: soimême.client.tableaux.suivreDonnées("orbitdb/...", x))
        soimême.assertEqual(expected, result)



