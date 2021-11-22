import unittest

from constellationPy import ClientSync
from .utils import Serveur, VRAI_SERVEUR


class TestSync(unittest.TestCase):
    def setUp(soimême) -> None:
        soimême.serveur = Serveur()
        soimême.serveur.__enter__()
        soimême.client = ClientSync()

    def test_action_sync(soimême):
        id_orbite = soimême.client.obtIdOrbite()
        soimême.assertIsInstance(id_orbite, str)

    @unittest.skipIf(VRAI_SERVEUR, "Test uniquement pour le faux serveur.")
    def test_sousmodule(soimême):
        test = soimême.client.ceci_est_un_test.de_sous_module()
        soimême.assertEqual(test, "C'est beau")

    def test_fonction_qui_nexiste_pas(soimême):
        with soimême.assertRaises(AttributeError):
            soimême.client.cette_fonction_nexiste_pas()

    def test_sousmodule_qui_nexiste_pas(soimême):
        with soimême.assertRaises(AttributeError):
            soimême.client.ce_module_nexiste_pas.ni_cette_fonction()

    @unittest.skip
    def test_suivre_sync(soimême):
        pass


    def test_obt_données_tableau(soimême):
        client = ClientSync()
        données = client.obt_données_tableau("orbitdb/...")
        soimême.assertEqual(expected, result)

    def test_obt_données_réseau(soimême):
        client = ClientSync()
        données = client.obt_données_réseau("clef unique bd", "clef unique tableau")
        soimême.assertEqual(expected, result)

    def tearDown(soimême) -> None:
        soimême.serveur.__exit__()
