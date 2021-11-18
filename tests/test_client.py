from unittest import TestCase

import trio

from constellationPy.client import ouvrir_client
from .ressources.faux_serveur import Serveur


class TestClient(TestCase):

    def setUp(soimême) -> None:
        soimême.serveur = Serveur()
        soimême.serveur.__enter__()

    async def test_action(soimême):
        async with ouvrir_client() as client:
            id_orbite = await client.obtIdOrbite()
            soimême.assertIsInstance(id_orbite, str)

    async def test_kebab_et_chameau(soimême):
        async with ouvrir_client() as client:
            id_kebab = await client.obt_id_orbite()
            id_chameau = await client.obtIdOrbite()
            soimême.assertEqual(id_kebab, id_chameau)

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

    async def test_suivre(soimême):
        canal_envoie, canal_réception = trio.open_memory_channel(0)

        async with ouvrir_client() as client:
            id_bd = await client.bds.créerBd("ODBl-1.0")
            id_tableau = await client.bds.ajouterTableauBd(id_bd)

            id_var = await client.variables.créerVariable("numérique")
            id_col = await client.tableaux.ajouterColonneTableau(id_tableau, id_var)

            async def f_suivre_données(éléments):
                async with canal_envoie:
                    await canal_envoie.send(éléments[0][id_col])

            oublier_données = await client.tableaux.suivreDonnées(id_tableau, f_suivre_données)
            await client.tableaux.ajouterÉlément(id_tableau, {id_col: 123})

            async with canal_réception:
                async for m in canal_réception:
                    soimême.assertEqual(m, 123)
            oublier_données()

    def tearDown(soimême) -> None:
        soimême.serveur.__exit__()


class Test(TestCase):

    @classmethod
    async def setUpClass(cls) -> None:
        cls.client = Client()
        await cls.client.__aenter__()

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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.__aexit__()
