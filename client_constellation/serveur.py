import subprocess
from typing import Optional


def _obt_version(commande: str, arg="-v") -> Optional[str]:
    try:
        résultat = subprocess.run([commande, arg], capture_output=True)
    except FileNotFoundError:
        return

    if résultat.returncode == 0:
        return résultat.stdout.decode()


def _assurer_constellation_installée():
    version_npm = obt_version_npm()
    if not version_npm:
        raise FileNotFoundError("Vous devez installer Node.js au https://nodejs.org/fr/download/.")

    version_yarn = obt_version_yarn()
    if not version_yarn:
        résultat_yarn = subprocess.run(["npm", "install", "-g", "yarn"], capture_output=True)
        if résultat_yarn.returncode != 0:
            raise ConnectionError(
                f"Erreur d'installation de Yarn :\n\t{résultat_yarn.stderr.decode()}"
            )

    version_constellation = obt_version_constellation()
    if not version_constellation:
        résultat_constellation = subprocess.run(["yarn", "global", "add", "@constl/serveur-ws"], capture_output=True)
        if résultat_constellation.returncode != 0:
            raise ConnectionError(
                f"Erreur d'installation de Constellation :\n\t{résultat_constellation.stderr.decode()}"
            )


def obt_version_constellation() -> Optional[str]:
    return _obt_version("constl-ws")


def obt_version_yarn() -> Optional[str]:
    return _obt_version("yarn")


def obt_version_npm() -> Optional[str]:
    return _obt_version("npm", "version")


def lancer_serveur(port=5000, autoinstaller=True) -> subprocess.Popen:
    if autoinstaller:
        _assurer_constellation_installée()
    version = obt_version_constellation()
    if not version:
        raise ChildProcessError("Constellation doit être installé sur votre appareil.")
    return subprocess.Popen(["constl-ws", "-p", str(port)])


context = {"serveur": None}


def changer_context(port: int):
    if context["serveur"] is not None:
        raise RuntimeError("On ne peut avoir qu'un serveur en context à la fois.")

    context["serveur"] = port


def effacer_context():
    context["serveur"] = None


def obtenir_context() -> Optional[int]:
    return context["serveur"]


class Serveur(object):

    def __init__(soimême, port=5000, autoinstaller=True):
        soimême.port = port
        soimême.autoinstaller = autoinstaller

        soimême.serveur: Optional[subprocess.Popen] = None

    def __enter__(soimême):
        changer_context(soimême.port)
        soimême.serveur = lancer_serveur(soimême.port, soimême.autoinstaller)

    def __exit__(soimême, exc_type, exc_val, exc_tb):
        effacer_context()
        soimême.serveur.terminate()
