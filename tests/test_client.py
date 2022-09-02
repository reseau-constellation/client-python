import json
import unittest
from unittest import TestCase

import trio

from constellationPy.client import ouvrir_client, Client
from tests.utils import Serveur, VRAI_SERVEUR


class TestClient(TestCase):
    serveur: Serveur

    @classmethod
    def setUpClass(cls) -> None:
        cls.serveur = Serveur()
        cls.serveur.__enter__()

    async def test_action(soimême):
        async with ouvrir_client() as client:
            id_orbite = await client.obtIdOrbite()
            soimême.assertIsInstance(id_orbite, str)

    async def test_kebab_et_chameau(soimême):
        async with ouvrir_client() as client:
            id_kebab = await client.obt_id_orbite()
            id_chameau = await client.obtIdOrbite()
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

            oublier()
            await client.changer_valeur_suivie(x=2)
            soimême.assertNotEqual(résultat["x"], 2)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_suivre_données(soimême):
        async with ouvrir_client() as client:
            print("client ouvert")
            id_bd = await client.bds.créerBd(licence="ODBl-1.0")
            print("id_bd", id_bd)
            id_tableau = await client.bds.ajouterTableauBd(id=id_bd)
            print("id_tableau", id_tableau)

            id_var = await client.variables.créerVariable(catégorie="numérique")
            print("id_var", id_var)
            id_col = await client.tableaux.ajouterColonneTableau(id_tableau=id_tableau, id_variable=id_var)
            print("id_col", id_col)

            résultat = {}

            def f_suivre_données(éléments):
                print("éléments", éléments)
                if éléments:
                    résultat["élément"] = éléments
                    soimême.assertEqual(éléments[0]["données"][id_col], 123)
                    oublier_données()

            oublier_données = await client.tableaux.suivreDonnées(id_tableau=id_tableau, f=f_suivre_données)
            print("oublier données")
            id_élément = await client.tableaux.ajouterÉlément(id_tableau=id_tableau, vals={id_col: 123})
            print("id_élément", id_élément)

            soimême.assertIsNotNone(résultat["élément"])

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_obt_données_tableau(soimême):
        async with ouvrir_client() as client:
            données = await client.obt_données_tableau("orbitdb/...")
        raise NotImplementedError
        # soimême.assertEqual(expected, result)

    @unittest.skipIf(not VRAI_SERVEUR, "Test uniquement pour le vrai serveur.")
    async def test_obt_données_réseau(soimême):
        async with ouvrir_client() as client:
            données = await client.obt_données_réseau("clef unique bd", "clef unique tableau")
        raise NotImplementedError
        # soimême.assertEqual(expected, result)

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

        print(erreurs)
        soimême.assertEqual(len(erreurs), 1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.__exit__()
