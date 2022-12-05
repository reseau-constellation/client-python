import logging
from unittest import TestCase

from constellationPy.client import ouvrir_client
from constellationPy.serveur import obtenir_contexte, ErreurConnexionContexteExistant
from tests.utils import Serveur

logging.basicConfig(level=logging.DEBUG)


class TestServeur(TestCase):

    async def test_détecter_port(soimême):
        port_serveur = 5006
        with Serveur(port_serveur):
            port_contexte = obtenir_contexte()
            soimême.assertEqual(port_contexte, port_serveur)

    async def test_erreur_deux_serveurs(soimême):
        with soimême.assertRaises(ErreurConnexionContexteExistant):
            with Serveur():
                with Serveur():
                    pass

    async def test_avec_contexte(soimême):
        port_serveur = 5007
        with Serveur(port_serveur):
            async with ouvrir_client() as client:
                port_client = client.port
                soimême.assertEqual(port_client, port_serveur)

    async def test_trouver_port_libre(soimême):
        with Serveur() as serveur:
            port_serveur = serveur.port
            port_contexte = obtenir_contexte()
            soimême.assertEqual(port_serveur, port_contexte)
