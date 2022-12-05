import os
import tempfile
from os import path
from typing import Optional

from constellationPy.const import EXE_CONSTL

VRAI_SERVEUR = os.getenv('VRAI_SERVEUR')
if VRAI_SERVEUR:
    from constellationPy.serveur import Serveur as ServeurOriginal, TypeExe


    class Serveur(ServeurOriginal):
        def __init__(
                soimême,
                port: Optional[int] = None,
                autoinstaller=True,
                exe: TypeExe = EXE_CONSTL
        ):
            soimême.dossier = tempfile.TemporaryDirectory()
            sfip = path.join(soimême.dossier.name, "sfip")
            orbite = path.join(soimême.dossier.name, "orbite")
            super().__init__(port=port, autoinstaller=autoinstaller, sfip=sfip, orbite=orbite, exe=exe)

        def __exit__(soimême, *args):
            super().__exit__(*args)
            try:
                soimême.dossier.cleanup()
            except NotADirectoryError:
                # Drôle d'erreur sur Windows
                pass

else:
    from .ressources.faux_serveur import Serveur

Serveur = Serveur
