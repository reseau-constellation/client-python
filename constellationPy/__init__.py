from importlib.metadata import version, PackageNotFoundError

from .client import ouvrir_client, Client
from .serveur import Serveur, lancer_serveur, mettre_constellation_à_jour, désinstaller_constellation
from .sync import ClientSync
from .utils import fais_rien, une_fois

try:
    __version__ = version("constellationPy")
except PackageNotFoundError:
    __version__ = None
