import json
import platform
import subprocess
from typing import Optional, TypedDict, Union, List, Tuple

import urllib3
from semantic_version import SimpleSpec, Version

from .const import V_SERVEUR_NÉCESSAIRE

TypeExe = Union[str, List[str]]
v_serveur_nécessaire = SimpleSpec(V_SERVEUR_NÉCESSAIRE)


def version_compatible(v: Union[str, None], réf: SimpleSpec) -> bool:
    return v and (Version(v) in réf)


def obt_versions_dispo_npm(paquet: str) -> List[str]:
    http = urllib3.PoolManager()
    r = http.request("GET", f"https://registry.npmjs.org/{paquet}")
    return list(json.loads(r.data.decode())["versions"].keys())


def _obt_version(commande: Union[str, List[str]], arg="-v") -> Optional[str]:
    if isinstance(commande, str):
        commande = [commande]

    try:
        résultat = subprocess.run([*commande, arg], capture_output=True)
        print("résultat", résultat)
    except FileNotFoundError as e:
        print("FileNotFoundError", e)
        return

    if résultat.returncode == 0:
        return résultat.stdout.decode().replace("\r", '').replace("\n", '')

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
    assurer_serveur_constl_installé()
    assurer_ipa_constl_installée()


def assurer_serveur_constl_installé():
    v_serveur = obt_version_serveur_constellation()
    if not version_compatible(v_serveur, v_serveur_nécessaire):
        assurer_npm_yarn_installés()
        installer_de_yarn("@constl/serveur", v_serveur_nécessaire)

    v_serveur = obt_version_serveur_constellation()

    if not version_compatible(v_serveur, v_serveur_nécessaire):
        raise ChildProcessError("Erreur d'installation du serveur Constellation.")


def assurer_ipa_constl_installée():
    version_ipa_constellation = obt_version_ipa_constellation()
    version_ipa_constellation_nécessaire = obt_version_ipa_constellation_nécessaire()
    if not version_compatible(version_ipa_constellation, version_ipa_constellation_nécessaire):
        assurer_npm_yarn_installés()
        installer_de_yarn("@constl/ipa", version_ipa_constellation_nécessaire)

    version = obt_version_ipa_constellation()

    if not version_compatible(version, version_ipa_constellation_nécessaire):
        raise ChildProcessError("Erreur d'installation de Constellation.")


def obt_version_ipa_constellation(exe: TypeExe = "constl") -> Optional[SimpleSpec]:
    return SimpleSpec(_obt_version(exe, "v-constl"))


def obt_version_ipa_constellation_nécessaire(exe: TypeExe = "constl") -> SimpleSpec:
    return SimpleSpec(_obt_version(exe, "v-constl-obli"))


def assurer_npm_yarn_installés():
    version_npm = obt_version_npm()
    if not version_npm:
        try:
            _installer_nodejs()
        except Exception:
            # Si on n'a pas réussi à l'installer pour vous, vous devrez le faire manuellement.
            raise FileNotFoundError("Vous devez installer Node.js au https://nodejs.org/fr/download/.")

    version_yarn = obt_version_yarn()
    if not version_yarn:
        résultat_yarn = subprocess.run(["npm", "install", "-g", "yarn"], capture_output=True)
        if résultat_yarn.returncode != 0:
            raise ConnectionError(
                f"Erreur d'installation de Yarn :\n\t{résultat_yarn.stderr.decode()}"
            )


def obt_version_serveur_constellation(exe: TypeExe = "constl") -> Optional[str]:
    return _obt_version(exe)


def installer_de_yarn(paquet: str, version: SimpleSpec):
    résultat_constellation = subprocess.run(
        ["yarn", "global", "add", paquet + "@" + version.expression],
        capture_output=True
    )

    if résultat_constellation.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation de Constellation :\n\t{résultat_constellation.stderr.decode()}"
        )


def obt_version_yarn() -> Optional[str]:
    return _obt_version("yarn")


def obt_version_npm() -> Optional[str]:
    return _obt_version("npm", "version")


def lancer_serveur(port=None, autoinstaller=True, exe: TypeExe = "constl") -> Tuple[subprocess.Popen, int]:
    if isinstance(exe, str):
        exe = [exe]

    if autoinstaller:
        assurer_constellation_installée()
    version = obt_version_serveur_constellation(exe)
    print("version", version, v_serveur_nécessaire)
    if not version_compatible(version, v_serveur_nécessaire):
        raise ChildProcessError(
            "Constellation doit être installée et à jour sur votre appareil. "
            "Vous pouvez utiliser assurer_constellation_installée() pour ce faire."
        )
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
