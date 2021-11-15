import unittest
from unittest import TestCase

import semantic_version as sv

from client_constellation.client import ouvrir_client
from .ressources.faux_serveur import Serveur


class TestClient(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.serveur = Serveur()
        cls.serveur.__enter__()

    async def test_kebab_et_chameau(soimême):
        async with ouvrir_client() as client:
            version_kebab = await client.obt_version()
            version_chameau = await client.obtVersion()
            soimême.assertEqual(version_kebab, version_chameau)

    @unittest.skip
    async def test_sousmodule(soimême):
        async with ouvrir_client() as client:
            id_orbite = await client.obtIdOrbite()
            soimême.assertIsInstance(id_orbite, str)

    async def test_action(soimême):
        async with ouvrir_client() as client:
            version = await client.obt_version()
            sv.SimpleSpec(version)

    async def test_suivre(soimême):
        async with ouvrir_client() as client:
            pass

    @classmethod
    def tearDownClass(cls) -> None:
        cls.serveur.__exit__()


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
