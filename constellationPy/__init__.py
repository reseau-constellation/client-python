from importlib.metadata import version

from .client import ouvrir_client, Client
from .serveur import Serveur, lancer_serveur, mettre_constellation_à_jour, désinstaller_constellation
from .sync import ClientSync
from .utils import fais_rien, une_fois

__version__ = version("constellationPy")
