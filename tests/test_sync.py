import unittest

import pandas as pd
import pandas.testing as pdt

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
        id_orbite = soimême.client.obtIdDispositif()
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
        soimême.client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})
        données = soimême.client.obt_données_tableau(id_tableau=id_tableau, formatDonnées="constellation")

        soimême.assertEqual(
            données,
            {
                'données': [{
                    id_col: 123,
                }],
                'fichiersSFIP': {},
                'nomTableau': id_tableau.lstrip('/orbitdb/')
            }
        )

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    def test_obt_données_tableau_noms_variables(soimême):
        id_bd = soimême.client.bds.créerBd(licence="ODBl-1.0")
        id_tableau = soimême.client.bds.ajouterTableauBd(id_bd=id_bd)

        id_var = soimême.client.variables.créerVariable(catégorie="numérique")
        id_col = soimême.client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
        soimême.client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})

        soimême.client.variables.sauvegarder_noms_variable(id_variable=id_var, noms={"fr": "Précipitation"})

        données = soimême.client.obt_données_tableau(id_tableau=id_tableau, langues=["த", "fr"])

        réf = pd.DataFrame({"Précipitation": [123]})
        pdt.assert_frame_equal(données.sort_index(axis=1), réf.sort_index(axis=1))

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    def test_obt_données_tableau_format_pandas(soimême):
        id_bd = soimême.client.bds.créerBd(licence="ODBl-1.0")
        id_tableau = soimême.client.bds.ajouterTableauBd(id_bd=id_bd)

        id_var = soimême.client.variables.créerVariable(catégorie="numérique")
        id_col = soimême.client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
        soimême.client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})

        données = soimême.client.obt_données_tableau(id_tableau=id_tableau)

        réf = pd.DataFrame({id_col: [123]})
        pdt.assert_frame_equal(données, réf)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    def test_obt_données_tableau_nuée(soimême):
        clef_tableau = "clef"

        id_nuée = soimême.client.nuées.créer_nuée()
        id_var = soimême.client.variables.créerVariable(catégorie="numérique")
        id_tableau = soimême.client.nuées.ajouterTableauNuée(
            idNuée=id_nuée,
            clefTableau=clef_tableau,
        )
        id_col = soimême.client.nuées.ajouterColonneTableauNuée(
            id_tableau=id_tableau,
            id_variable=id_var
        )
        schéma = soimême.client.nuées.générerSchémaBdNuée(id_nuée=id_nuée, licence="ODbl-1_0")

        soimême.client.bds.ajouterÉlémentÀTableauUnique(
            schémaBd=schéma,
            id_nuée_unique=id_nuée,
            clefTableau=clef_tableau,
            vals={id_col: 123}
        )

        données = soimême.client.obt_données_tableau_nuée(
            id_nuée=id_nuée, clef_tableau=clef_tableau,
            n_résultats_désirés=100, formatDonnées="constellation"
        )

        idCompte = soimême.client.obt_id_compte()

        soimême.assertEqual(
            données, {
                'données': [{
                    'auteur': idCompte,
                    id_col: 123,
                }],
                'fichiersSFIP': {},
                'nomTableau': clef_tableau, }
        )

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    def test_obt_données_tableau_nuée_format_pandas(soimême):
        clef_tableau = "clef"

        id_nuée = soimême.client.nuées.créer_nuée()
        id_var = soimême.client.variables.créerVariable(catégorie="numérique")
        id_tableau = soimême.client.nuées.ajouterTableauNuée(
            idNuée=id_nuée,
            clefTableau=clef_tableau,
        )
        id_col = soimême.client.nuées.ajouterColonneTableauNuée(
            id_tableau=id_tableau,
            id_variable=id_var
        )
        schéma = soimême.client.nuées.générerSchémaBdNuée(id_nuée=id_nuée, licence="ODbl-1_0")

        soimême.client.bds.ajouterÉlémentÀTableauUnique(
            schémaBd=schéma,
            id_nuée_unique=id_nuée,
            clefTableau=clef_tableau,
            vals={id_col: 123}
        )

        données = soimême.client.obt_données_tableau_nuée(
            id_nuée=id_nuée, clef_tableau=clef_tableau,
            n_résultats_désirés=100
        )
        idCompte = soimême.client.obtIdCompte()

        réf = pd.DataFrame({id_col: [123], "auteur": idCompte})
        pdt.assert_frame_equal(données, réf)


    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.__exit__()
