import os

VRAI_SERVEUR = os.getenv('VRAI_SERVEUR')
if VRAI_SERVEUR:
    from constellationPy.serveur import Serveur
else:
    from .ressources.faux_serveur import Serveur

Serveur = Serveur
