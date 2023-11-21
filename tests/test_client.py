import json
import tempfile
import unittest
from unittest import TestCase

import pandas as pd
import pandas.testing as pdt
import trio

from constellationPy.client import ouvrir_client, Client
from tests.utils import Serveur, VRAI_SERVEUR


class TestClient(TestCase):
    dossier: tempfile.TemporaryDirectory
    serveur: Serveur

    @classmethod
    def setUpClass(cls) -> None:
        cls.serveur = Serveur()
        cls.serveur.__enter__()

    async def test_action(soimême):
        async with ouvrir_client() as client:
            id_orbite = await client.obtIdDispositif()
        soimême.assertIsInstance(id_orbite, str)

    async def test_kebab_et_chameau(soimême):
        async with ouvrir_client() as client:
            id_kebab = await client.obt_id_dispositif()
            id_chameau = await client.obtIdDispositif()
            soimême.assertEqual(id_kebab, id_chameau)

    @unittest.skipIf(VRAI_SERVEUR, "Test uniquement pour le faux serveur.")
    async def test_sousmodule(soimême):
        async with ouvrir_client() as client:
            test = await client.ceci_est_un_test.de_sous_module()
        soimême.assertEqual(test, "C'est beau")

    async def test_fonction_qui_nexiste_pas(soimême):
        with soimême.assertRaises(AttributeError):
            async with ouvrir_client() as client:
                await client.cette_fonction_nexiste_pas()

    async def test_sousmodule_qui_nexiste_pas(soimême):
        with soimême.assertRaises(AttributeError):
            async with ouvrir_client() as client:
                await client.ce_module_nexiste_pas.ni_cette_fonction()

    @unittest.skipIf(VRAI_SERVEUR, "Test uniquement pour le faux serveur.")
    async def test_suivre(soimême):
        résultat = {}

        def traiter_résultat(x):
            résultat["x"] = x

        async with ouvrir_client() as client:
            oublier = await client.fonction_suivi(f=traiter_résultat)
            await client.changer_valeur_suivie(x=3)
            soimême.assertEqual(résultat["x"], 3)

            await oublier()
            await client.changer_valeur_suivie(x=2)
            soimême.assertNotEqual(résultat["x"], 2)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_suivre_données(soimême):
        async with ouvrir_client() as client:
            id_bd = await client.bds.créerBd(licence="ODBl-1.0")
            id_tableau = await client.bds.ajouterTableauBd(id_bd=id_bd)

            id_var = await client.variables.créerVariable(catégorie="numérique")
            id_col = await client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)

            résultat = {}
            prêt = trio.Event()

            async def f_suivre_données(éléments):
                if éléments:
                    prêt.set()
                    résultat["élément"] = éléments
                    await oublier_données()

            oublier_données = await client.tableaux.suivreDonnées(id_tableau=id_tableau, f=f_suivre_données)
            await client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})

            await prêt.wait()

            soimême.assertIsNotNone(résultat["élément"])
            soimême.assertEqual(résultat["élément"][0]["données"][id_col], 123)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_obt_données_tableau(soimême):
        async with ouvrir_client() as client:
            id_bd = await client.bds.créerBd(licence="ODBl-1.0")
            id_tableau = await client.bds.ajouterTableauBd(id_bd=id_bd)

            id_var = await client.variables.créerVariable(catégorie="numérique")
            id_col = await client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
            await client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})

            données = await client.obt_données_tableau(id_tableau=id_tableau, formatDonnées="constellation")

        soimême.assertEqual(
            données,
            {
                'données': [{
                    id_col: 123,
                }],
                'fichiersSFIP': {},
                'nomTableau': id_tableau.lstrip("/orbitdb/")
            }
        )

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_obt_données_tableau_noms_variables(soimême):
        async with ouvrir_client() as client:
            id_bd = await client.bds.créerBd(licence="ODbl-1.0")
            id_tableau = await client.bds.ajouterTableauBd(id_bd=id_bd)

            id_var = await client.variables.créerVariable(catégorie="numérique")
            id_col = await client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
            await client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})
            await client.variables.sauvegarder_noms_variable(id_variable=id_var, noms={"fr": "Précipitation"})

            données = await client.obt_données_tableau(
                id_tableau=id_tableau, langues=["த", "fr"]
            )

        réf = pd.DataFrame({"Précipitation": [123]})
        pdt.assert_frame_equal(données.sort_index(axis=1), réf.sort_index(axis=1))

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_obt_données_tableau_format_pandas(soimême):

        async with ouvrir_client() as client:
            id_bd = await client.bds.créerBd(licence="ODBl-1.0")
            id_tableau = await client.bds.ajouterTableauBd(id_bd=id_bd)

            id_var = await client.variables.créerVariable(catégorie="numérique")
            id_col = await client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
            await client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})

            données = await client.obt_données_tableau(id_tableau=id_tableau)

        réf = pd.DataFrame({id_col: [123]})
        pdt.assert_frame_equal(données, réf)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_obt_données_tableau_nuée(soimême):
        async with ouvrir_client() as client:
            clef_tableau = "clef"

            id_nuée = await client.nuées.créer_nuée()
            id_var = await client.variables.créerVariable(catégorie="numérique")
            id_tableau = await client.nuées.ajouterTableauNuée(
                idNuée=id_nuée,
                clefTableau=clef_tableau,
            )
            id_col = await client.nuées.ajouterColonneTableauNuée(
                id_tableau=id_tableau,
                id_variable=id_var
            )
            schéma = await client.nuées.générerSchémaBdNuée(id_nuée=id_nuée, licence="ODbl-1_0")

            await client.bds.ajouterÉlémentÀTableauUnique(
                schémaBd=schéma,
                id_nuée_unique=id_nuée,
                clefTableau=clef_tableau,
                vals={id_col: 123}
            )

            données = await client.obt_données_tableau_nuée(
                id_nuée=id_nuée, clef_tableau=clef_tableau,
                n_résultats_désirés=100, formatDonnées="constellation"
            )

            idCompte = await client.obt_id_compte()

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
    async def test_obt_données_tableau_nuée_format_pandas(soimême):
        async with ouvrir_client() as client:
            clef_tableau = "clef"

            id_nuée = await client.nuées.créer_nuée()
            id_var = await client.variables.créerVariable(catégorie="numérique")
            id_tableau = await client.nuées.ajouterTableauNuée(
                idNuée=id_nuée,
                clefTableau=clef_tableau,
            )
            id_col = await client.nuées.ajouterColonneTableauNuée(
                id_tableau=id_tableau,
                id_variable=id_var
            )
            schéma = await client.nuées.générerSchémaBdNuée(id_nuée=id_nuée, licence="ODbl-1_0")

            await client.bds.ajouterÉlémentÀTableauUnique(
                schémaBd=schéma,
                id_nuée_unique=id_nuée,
                clefTableau=clef_tableau,
                vals={id_col: 123}
            )

            données = await client.obt_données_tableau_nuée(
                id_nuée=id_nuée, clef_tableau=clef_tableau,
                n_résultats_désirés=100
            )
            idCompte = await client.obtIdCompte()

        réf = pd.DataFrame({id_col: [123], "auteur": idCompte})
        pdt.assert_frame_equal(données, réf)

    @unittest.skipIf(VRAI_SERVEUR, "Test uniquement pour le faux serveur.")
    async def test_fonctions_retour(soimême):
        résultat = {}

        prêt = trio.Event()
        six_résultats = trio.Event()

        def traiter_résultat(x):
            résultat["x"] = x
            prêt.set()
            if len(x) >= 6:
                six_résultats.set()

        async with ouvrir_client() as client:
            fs = await client.fonction_recherche(f=traiter_résultat, nRésultatsDésirés=3)
            await prêt.wait()
            soimême.assertListEqual(résultat["x"], list(range(3)))

            await fs["fChangerN"](6)
            await six_résultats.wait()
            soimême.assertListEqual(résultat["x"], list(range(6)))

            # Plus de changements après fOublier
            await fs["fOublier"]()
            await fs["fChangerN"](3)
            await trio.sleep(.2)
            soimême.assertListEqual(résultat["x"], list(range(6)))

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_recherche(soimême):
        résultat = {}

        deux_résultats = trio.Event()
        un_résultat = trio.Event()
        deux_à_nouveau = trio.Event()

        def fonction_suivi_recherche(x):
            résultat["vars"] = x
            if len(x) > 1:
                if un_résultat.is_set():
                    deux_à_nouveau.set()
                else:
                    deux_résultats.set()
            elif deux_résultats.is_set() and len(x) == 1:
                un_résultat.set()

        async with ouvrir_client() as client:
            id_var_tmaxi = await client.variables.créerVariable(catégorie="numérique")
            await client.variables.sauvegarder_noms_variable(
                idVariable=id_var_tmaxi,
                noms={"fr": "Température maximale"}
            )

            id_var_tmini = await client.variables.créerVariable(catégorie="numérique")
            await client.variables.sauvegarder_noms_variable(
                idVariable=id_var_tmini,
                noms={"fr": "Température minimale"}
            )

            fs = await client.recherche.rechercher_variables_selon_nom(
                nom_variable="Température",
                f=fonction_suivi_recherche,
                nRésultatsDésirés=2
            )
            await deux_résultats.wait()
            soimême.assertEqual(2, len(résultat["vars"]), "Taille initiale")

            await fs["fChangerN"](1)
            await un_résultat.wait()
            soimême.assertEqual(1, len(résultat["vars"]), "Diminuer taille")

            await fs["fChangerN"](2)
            await deux_à_nouveau.wait()
            soimême.assertEqual(2, len(résultat["vars"]), "Augmenter taille")

            await fs["fOublier"]()

    async def test_canal_erreurs(soimême):

        async def coroutine_client(pouponnière_, canal_envoie_erreur_):
            async with canal_envoie_erreur_:
                async with Client(pouponnière_) as client:
                    await client.connecter(canal_envoie_erreur_)
                    await client.cette_fonction_nexiste_pas()

        erreurs = []

        async def coroutine_erreurs(canal_reçoie_erreur_):
            async with canal_reçoie_erreur_:
                async for erreur in canal_reçoie_erreur_:
                    erreurs.append(json.loads(erreur))

        async with trio.open_nursery() as pouponnière:
            canal_envoie_erreur, canal_reçoit_erreur = trio.open_memory_channel(0)

            pouponnière.start_soon(coroutine_client, pouponnière, canal_envoie_erreur)
            pouponnière.start_soon(coroutine_erreurs, canal_reçoit_erreur)

        soimême.assertEqual(len(erreurs), 1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.__exit__()
