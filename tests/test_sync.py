import unittest

from constellationPy import ClientSync, fais_rien
from tests.utils import Serveur, VRAI_SERVEUR


class TestSync(unittest.TestCase):
    serveur: Serveur

    @classmethod
    def setUpClass(cls) -> None:
        cls.serveur = Serveur()
        cls.serveur.__enter__()
        cls.client = ClientSync()

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

    @unittest.skipIf(VRAI_SERVEUR, "Test uniquement pour le faux serveur")
    def test_suivre_sync(soimême):
        soimême.client.changer_valeur_suivie(x=3)
        résultat = soimême.client.fonction_suivi(f=fais_rien)
        soimême.assertEqual(résultat, 3)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur")
    def test_obt_données_tableau(soimême):
        id_bd = soimême.client.bds.créerBd(licence="ODBl-1.0")
        id_tableau = soimême.client.bds.ajouterTableauBd(id_bd=id_bd)

        id_var = soimême.client.variables.créerVariable(catégorie="numérique")
        id_col = soimême.client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
        id_élément = soimême.client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})
        données = soimême.client.obt_données_tableau(id_tableau=id_tableau)

        soimême.assertEqual(données, [
            {
                'données': {
                    id_col: 123, 'id': données[0]['données']['id']
                }, 'empreinte': id_élément
            }
        ])

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur")
    def test_obt_données_réseau(soimême):
        # client = ClientSync()
        # données = client.obt_données_réseau("clef unique bd", "clef unique tableau")
        # print(données)
        raise NotImplementedError
        # soimême.assertEqual(expected, result)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.__exit__()
