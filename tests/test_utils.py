from unittest import TestCase

from client_constellation.utils import à_chameau


class TestUtils(TestCase):
    def test_à_chameau(soimême):
        chameau = à_chameau("suivre_données_tableau")
        soimême.assertEqual(chameau, "suivreDonnéesTableau")
