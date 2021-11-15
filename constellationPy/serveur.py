import subprocess
from typing import Optional, TypedDict, Union, List, Tuple

TypeExe = Union[str, List[str]]


def _obt_version(commande: Union[str, List[str]], arg="-v") -> Optional[str]:
    if isinstance(commande, str):
        commande = [commande]

    try:
        résultat = subprocess.run([*commande, arg], capture_output=True)
    except FileNotFoundError:
        return

    if résultat.returncode == 0:
        return résultat.stdout.decode()

    print(f"Erreur serveur Constellation: {résultat}")


def _assurer_constellation_installée():
    version_constellation = obt_version_constellation()
    if not version_constellation:

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

        for paquet in ["@constl/ipa", "@constl/serveur"]:
            résultat_constellation = subprocess.run(["yarn", "global", "add", paquet], capture_output=True)
            if résultat_constellation.returncode != 0:
                raise ConnectionError(
                    f"Erreur d'installation de Constellation :\n\t{résultat_constellation.stderr.decode()}"
                )


def obt_version_constellation(exe: TypeExe = "constl") -> Optional[str]:
    return _obt_version(exe)


def obt_version_yarn() -> Optional[str]:
    return _obt_version("yarn")


def obt_version_npm() -> Optional[str]:
    return _obt_version("npm", "version")


def lancer_serveur(port=None, autoinstaller=True, exe: TypeExe = "constl") -> Tuple[subprocess.Popen, int]:
    if isinstance(exe, str):
        exe = [exe]

    if autoinstaller:
        _assurer_constellation_installée()
    version = obt_version_constellation(exe)

    if not version:
        raise ChildProcessError("Constellation doit être installé sur votre appareil.")
    cmd = [*exe, "lancer"]
    if port:
        cmd += ["-p", str(port)]
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, bufsize=0, universal_newlines=True
    )
    for ligne in iter(p.stdout.readline, b''):
        if not ligne:
            break
        if ligne.startswith("Serveur prêt sur port :"):
            port = int(ligne.split(":")[1])
            break
    return p, port


type_context = TypedDict("type_context", {"port_serveur": Optional[int]})
context: type_context = {"port_serveur": None}


def changer_context(port: int):
    if context["port_serveur"] is not None:
        raise RuntimeError("On ne peut avoir qu'un serveur en context à la fois.")

    context["port_serveur"] = port


def effacer_context():
    context["port_serveur"] = None


def obtenir_context() -> Optional[int]:
    return context["port_serveur"]


class Serveur(object):

    def __init__(soimême, port=None, autoinstaller=True, exe: TypeExe = "constl"):
        soimême.port = port
        soimême.autoinstaller = autoinstaller
        soimême.exe = exe

        soimême.serveur: Optional[subprocess.Popen] = None

    def __enter__(soimême):
        soimême.serveur, soimême.port = lancer_serveur(soimême.port, soimême.autoinstaller, soimême.exe)
        changer_context(soimême.port)
        return soimême

    def __exit__(soimême, *args):
        effacer_context()
        soimême.serveur.terminate()
