import platform
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


def _installer_nodejs():
    système_opératoire = platform.system()

    options_installation = {
        "Linux": [["sudo apt install nodejs npm"]],
        "Darwin": [["brew update", "brew doctor", "brew install node"]],
        "Windows": [["scoop install nodejs"], ["cinst nodejs.install"]]
    }

    for option in options_installation[système_opératoire]:
        try:
            for cmd in option:
                subprocess.run(cmd.split())
            if obt_version_npm():
                return
        except FileNotFoundError:
            pass  # Si ça n'a pas fonctionné, on essayera la prochaine !

    # Système opératoire inconnu, ou bien rien n'a fonctionné
    raise OSError(système_opératoire)


def assurer_constellation_installée():
    version_constellation = obt_version_constellation()
    if not version_constellation:

        version_npm = obt_version_npm()
        if not version_npm:
            try:
                _installer_nodejs()
            except Exception:
                # Si on a pas réussi à l'installer pour vous, vous devrez le faire manuellement.
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

    version = obt_version_constellation()

    if not version:
        raise ChildProcessError("Erreur d'installation de Constellation.")


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
        assurer_constellation_installée()
    version = obt_version_constellation(exe)

    if not version:
        raise ChildProcessError("Constellation doit être installée sur votre appareil.")
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


def changer_contexte(port: int):
    if context["port_serveur"] is not None:
        raise ConnectionError("On ne peut avoir qu'un seule serveur en contexte à la fois.")

    context["port_serveur"] = port


def effacer_contexte():
    context["port_serveur"] = None


def obtenir_contexte() -> Optional[int]:
    return context["port_serveur"]


class Serveur(object):

    def __init__(soimême, port: Optional[int] = None, autoinstaller=True, exe: TypeExe = "constl"):
        soimême.port = port
        soimême.autoinstaller = autoinstaller
        soimême.exe = exe

        soimême.serveur: Optional[subprocess.Popen] = None

    def __enter__(soimême):
        soimême.serveur, soimême.port = lancer_serveur(soimême.port, soimême.autoinstaller, soimême.exe)
        changer_contexte(soimême.port)
        return soimême

    def __exit__(soimême, *args):
        effacer_contexte()
        soimême.serveur.terminate()
