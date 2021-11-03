import os
import subprocess
import sys

from client_constellation.serveur import changer_context, Serveur as ServeurOriginal

dir_serveur = os.path.join(os.path.split(__file__)[0], "_serveur.py")


class Serveur(ServeurOriginal):
    def __enter__(soimême):
        changer_context(soimême.port)
        soimême.serveur = subprocess.Popen([sys.executable, dir_serveur, "-p", str(soimême.port)])
