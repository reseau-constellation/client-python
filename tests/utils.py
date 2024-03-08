import os
import tempfile
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
            soimême.dossier_tempo = tempfile.TemporaryDirectory()
            super().__init__(port=port, autoinstaller=autoinstaller, dossier=soimême.dossier_tempo.name, exe=exe)

        def __exit__(soimême, *args):
            super().__exit__(*args)
            try:
                soimême.dossier_tempo.cleanup()
            except (NotADirectoryError, PermissionError):
                # Drôle d'erreur sur Windows
                pass

else:
    from .ressources.faux_serveur import Serveur

Serveur = Serveur
