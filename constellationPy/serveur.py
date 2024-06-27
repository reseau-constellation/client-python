import json
import logging
import platform
import subprocess
from functools import lru_cache
from typing import Optional, TypedDict, Union, List, Tuple

import urllib3
from semantic_version import SimpleSpec, Version

from .const import V_SERVEUR_NÉCESSAIRE, PAQUET_SERVEUR, EXE_CONSTL

TypeExe = Union[str, List[str]]
versions_serveur_compatibles = SimpleSpec(V_SERVEUR_NÉCESSAIRE)


class ErreurInstallationConstellation(ChildProcessError):
    pass


def lancer_serveur(
        port=None,
        autoinstaller=True,
        dossier: Optional[str] = None,
        exe: TypeExe = EXE_CONSTL
) -> Tuple[subprocess.Popen, int, str]:
    if isinstance(exe, str):
        exe = [exe]

    if autoinstaller:
        try:
            vérifier_installation_constellation(exe)
        except ErreurInstallationConstellation:
            mettre_constellation_à_jour(exe)

    vérifier_installation_constellation(exe)

    cmd = [*exe, "lancer", "-m"]
    if port:
        cmd += ["-p", str(port)]
    if dossier:
        cmd += [f"--dossier={dossier}"]

    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, bufsize=0,
        text=True,
        encoding="utf-8",
        shell=platform.system() == "Windows"
    )

    for ligne in iter(p.stdout.readline, ''):
        logging.debug("Message du serveur : " + ligne)

        if "MESSAGE MACHINE" in ligne:
            message = json.loads(ligne.split(":", 1)[1])
            if message["type"] == "NŒUD PRÊT":
                port = message["port"]
                code_secret = message["codeSecret"]
                return p, port, code_secret

    raise ConnectionError("Le serveur n'a pas répondu.")


type_contexte = TypedDict("type_contexte", {"port_serveur": Optional[int], "code_secret": Optional[str]})
context: type_contexte = {"port_serveur": None, "code_secret": None}


class ErreurConnexionContexteExistant(ConnectionError):
    def __init__(soimême):
        super().__init__("On ne peut avoir qu'un seule serveur en contexte à la fois.")


def changer_contexte(port: int, code_secret: str):
    if context["port_serveur"] is not None:
        raise ErreurConnexionContexteExistant()

    context["port_serveur"] = port
    context["code_secret"] = code_secret


def effacer_contexte():
    context["port_serveur"] = None
    context["code_secret"] = None


def obtenir_contexte() -> type_contexte:
    return context


def obtenir_port_contexte() -> Optional[str]:
    return obtenir_contexte()["port_serveur"]


def obtenir_code_secret_contexte() -> Optional[str]:
    return obtenir_contexte()["code_secret"]


def mettre_constellation_à_jour(exe: TypeExe = EXE_CONSTL):
    logging.debug("Mise à jour de Constellation")
    assurer_npm_pnpm_installés()

    mettre_serveur_à_jour(exe)


def mettre_serveur_à_jour(exe: TypeExe = EXE_CONSTL):
    version_serveur = obt_version_serveur(exe)

    if not serveur_compatible(version_serveur):
        version_serveur_désirée = obt_version_serveur_plus_récente_compatible()
        logging.debug(
            f"Mise à jour du serveur Constellation (version présente : {version_serveur}; "
            f"version désirée : {version_serveur_désirée})")
        installer_serveur(version_serveur_désirée)


def obt_version_serveur(exe: TypeExe = EXE_CONSTL) -> Optional[Version]:
    if v := _obt_version(exe, "version"):
        return Version(v)


def serveur_compatible(version: Version) -> bool:
    return version_compatible(version, versions_serveur_compatibles)


def version_compatible(v: Optional[Version], réf: SimpleSpec) -> bool:
    return v and (v in réf)


def obt_version_serveur_plus_récente_compatible() -> Version:
    versions_disponibles = obt_versions_dispo_npm(PAQUET_SERVEUR)
    versions_disponibles.sort(reverse=True)
    return next(v for v in versions_disponibles if serveur_compatible(v))


def obt_versions_dispo_npm(paquet: str) -> List[Version]:
    http = urllib3.PoolManager()
    r = http.request("GET", f"https://registry.npmjs.org/{paquet}")
    return [Version(v) for v in json.loads(r.data.decode())["versions"].keys()]


def _obt_version(commande: TypeExe, arg="-v") -> Optional[str]:
    if isinstance(commande, str):
        commande = [commande]

    try:
        résultat = subprocess.run([*commande, arg], capture_output=True, shell=platform.system() == "Windows")
    except FileNotFoundError:
        logging.debug("FileNotFoundError " + str([*commande, arg]))
        return

    logging.debug(résultat.returncode)
    logging.debug("stdout: " + résultat.stdout.decode())
    logging.debug("stderr: " + résultat.stderr.decode())
    if résultat.returncode == 0:
        return résultat.stdout.decode().replace("\r", '').replace("\n", '')
    elif "is not recognized as an internal or external command" in résultat.stderr.decode():
        return

    raise ChildProcessError(
        f"Erreur obtention de version pour {commande}: {résultat.stdout.decode()} {résultat.stderr.decode()}"
    )


def installer_serveur(version: Version):
    assurer_npm_pnpm_installés()

    code_installation = subprocess.Popen(
        ["curl", "https://raw.githubusercontent.com/reseau-constellation/serveur-ws/principale/installer.cjs"],
        stdout=subprocess.PIPE,
    )
    résultat = subprocess.Popen(["node", "-"], stdin=code_installation.stdout)
    code_installation.stdout.close()
    résultat.communicate()

    if résultat.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation Constellation :\n\t{résultat.stderr.decode() if résultat.stderr else None}"
            f"\n\t{résultat.stdout.decode() if résultat.stdout else None}"
        )


def désinstaller_constellation():
    try:
        désinstaller_serveur()
    except ConnectionError as é:
        if "This module isn't specified in a package.json file." in str(é):
            pass
        else:
            raise é


def désinstaller_serveur():
    désinstaller_de_pnpm(PAQUET_SERVEUR)


@lru_cache
def _vérifier_installation(exe_: Union[str, Tuple[str]]) -> True:
    message_erreur = "Constellation doit être installée et à jour sur votre appareil. " \
                     "Vous pouvez utiliser `mettre_constellation_à_jour()` pour ce faire. " \
                     "\nSi vous avez toujours des problèmes, vous pouvez utiliser `désinstaller_constellation()`" \
                     "pour nettoyer une installation brisée."

    if isinstance(exe_, tuple):
        exe_ = list(exe_)

    # Obtenir version serveur
    version_serveur = obt_version_serveur(exe_)
    logging.debug("version_serveur: " + str(version_serveur))

    # Si serveur non installé, erreur
    if not version_serveur:
        raise ErreurInstallationConstellation(message_erreur)

    # Vérifier version @constl/serveur compatible avec client python
    if not serveur_compatible(version_serveur):
        raise ErreurInstallationConstellation(
            message_erreur + f"\nVersion présente de {PAQUET_SERVEUR} : {version_serveur}"
        )


def vérifier_installation_constellation(exe: TypeExe = EXE_CONSTL):
    return _vérifier_installation(exe if isinstance(exe, str) else tuple(exe))


def assurer_npm_pnpm_installés():
    version_npm = obt_version_npm()
    if not version_npm:
        logging.debug("Installation de npm")
        try:
            _installer_nodejs()
        except Exception:
            # Si on n'a pas réussi à l'installer pour vous, vous devrez le faire manuellement.
            raise FileNotFoundError("Vous devez installer Node.js au https://nodejs.org/en/download.")

    version_pnpm = obt_version_pnpm()
    if not version_pnpm:
        logging.debug("Installation de pnpm")
        résultat_npm = subprocess.run(
            ["npm", "install", "-g", "pnpm"], capture_output=True, shell=platform.system() == "Windows"
        )
        if résultat_npm.returncode != 0:
            raise ConnectionError(
                f"Erreur d'installation de PNPM :\n\t{résultat_npm.stderr.decode()}"
                f"\n\t{résultat_npm.stdout.decode()}"
            )


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
                subprocess.run(cmd.split(), shell=platform.system() == "Windows")
            if obt_version_npm():
                return
        except FileNotFoundError:
            pass  # Si ça n'a pas fonctionné, on essayera la prochaine !

    # Système opératoire inconnu, ou bien rien n'a fonctionné
    raise OSError(système_opératoire)


def désinstaller_de_pnpm(paquet):
    assurer_npm_pnpm_installés()
    résultat_pnpm = subprocess.run(
        ["pnpm", "remove", "-g", paquet],
        capture_output=True,
        shell=platform.system() == "Windows"
    )

    if résultat_pnpm.returncode != 0:
        raise ConnectionError(
            f"Erreur de désinstallation du paquet {paquet} :\n\t{résultat_pnpm.stderr.decode()}"
        )


def obt_version_pnpm() -> Optional[str]:
    return _obt_version("pnpm")


def obt_version_npm() -> Optional[str]:
    return _obt_version("npm", "-v")


class Serveur(object):
    def __init__(
            soimême,
            port: Optional[int] = None,
            autoinstaller=True,
            dossier: Optional[str] = None,
            exe: TypeExe = EXE_CONSTL
    ):
        soimême.port = port
        soimême.autoinstaller = autoinstaller
        soimême.exe = exe

        soimême.dossier = dossier

        soimême.serveur: Optional[subprocess.Popen] = None

    def __enter__(soimême):
        if obtenir_port_contexte():
            raise ErreurConnexionContexteExistant()
        soimême.serveur, soimême.port, soimême.code_secret = lancer_serveur(
            port=soimême.port,
            autoinstaller=soimême.autoinstaller,
            dossier=soimême.dossier,
            exe=soimême.exe
        )
        changer_contexte(soimême.port, soimême.code_secret)
        return soimême

    def __exit__(soimême, *args):
        effacer_contexte()
        soimême.serveur.stdin.write("\n")
        soimême.serveur.terminate()
