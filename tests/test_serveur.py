from unittest import TestCase

# import semantic_version as sv

from client_constellation.client import ouvrir_client
from client_constellation.serveur import obtenir_context
from tests.ressources.faux_serveur import Serveur


class TestServeur(TestCase):

    async def test_détecter_port(soimême):
        with Serveur(5001):
            port = obtenir_context()
            soimême.assertEqual(port, 5001)

    async def test_avec_context(soimême):
        with Serveur(5000):
            async with ouvrir_client() as client:
                version = client.obtVersion()
                sv.SimpleSpec(version)
