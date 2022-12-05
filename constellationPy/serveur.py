import json
import logging
import platform
import subprocess
from functools import lru_cache
from typing import Optional, TypedDict, Union, List, Tuple

import urllib3
from semantic_version import SimpleSpec, Version

from .const import V_SERVEUR_NÉCESSAIRE, PAQUET_SERVEUR, PAQUET_IPA, EXE_CONSTL

TypeExe = Union[str, List[str]]
versions_serveur_compatibles = SimpleSpec(V_SERVEUR_NÉCESSAIRE)


class ErreurInstallationConstellation(ChildProcessError):
    pass


def lancer_serveur(
        port=None,
        autoinstaller=True,
        sfip: Optional[Union[str, int]] = None,
        orbite: Optional[str] = None,
        exe: TypeExe = EXE_CONSTL
) -> Tuple[subprocess.Popen, int]:
    if isinstance(exe, str):
        exe = [exe]

    if autoinstaller:
        try:
            vérifier_installation_constellation(exe)
        except ErreurInstallationConstellation:
            mettre_constellation_à_jour(exe)

    vérifier_installation_constellation(exe)

    cmd = [*exe, "lancer"]
    if port:
        cmd += ["-p", str(port)]
    if orbite:
        cmd += [f"--doss-orbite={orbite}"]
    if sfip:
        cmd += [f"--doss-sfip={sfip}"]

    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, bufsize=0, text=True,
        shell=platform.system() == "Windows"
    )
    for ligne in iter(p.stdout.readline, b''):
        if not ligne:
            break
        if ligne.startswith("Serveur prêt sur port :"):
            port = int(ligne.split(":")[1])
            break

    return p, port


type_contexte = TypedDict("type_contexte", {"port_serveur": Optional[int]})
context: type_contexte = {"port_serveur": None}


class ErreurConnexionContexteExistant(ConnectionError):
    def __init__(soimême):
        super().__init__("On ne peut avoir qu'un seule serveur en contexte à la fois.")


def changer_contexte(port: int):
    if context["port_serveur"] is not None:
        raise ErreurConnexionContexteExistant()

    context["port_serveur"] = port


def effacer_contexte():
    context["port_serveur"] = None


def obtenir_contexte() -> Optional[int]:
    return context["port_serveur"]


def mettre_constellation_à_jour(exe: TypeExe = EXE_CONSTL):
    logging.info("Mise à jour de Constellation")
    assurer_npm_pnpm_installés()

    mettre_serveur_à_jour(exe)
    mettre_ipa_à_jour(exe)


def mettre_serveur_à_jour(exe: TypeExe = EXE_CONSTL):
    version_serveur = obt_version_serveur(exe)
    if not serveur_compatible(version_serveur):
        version_serveur_désirée = obt_version_serveur_plus_récente_compatible()
        logging.info(
            f"Mise à jour du serveur Constellation (version présente : {version_serveur}; "
            f"version désirée : {version_serveur_désirée})")
        installer_serveur(version_serveur_désirée)


def obt_version_serveur(exe: TypeExe = EXE_CONSTL) -> Optional[Version]:
    try:
        if v := _obt_version(exe, "version"):
            print("ici 1", v)
            return Version(v)
    except ChildProcessError as é:
        if f"Error: Cannot find module '{PAQUET_IPA}'" in str(é):
            print("ici 2", str(é))
            return
        else:
            raise é


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
        print("FileNotFoundError", [*commande, arg])
        return
    print("résultat", résultat)
    print("returncode", résultat.returncode)
    print("stdout", résultat.stdout.decode())
    print("stderr", résultat.stderr.decode())
    if résultat.returncode == 0:
        return résultat.stdout.decode().replace("\r", '').replace("\n", '')

    raise ChildProcessError(
        f"Erreur obtention de version pour {commande}: {résultat.stdout.decode()} {résultat.stderr.decode()}"
    )


def installer_serveur(version: Version):
    installer_de_pnpm(PAQUET_SERVEUR, version)


def mettre_ipa_à_jour(exe: TypeExe = EXE_CONSTL):
    # Si @constl/ipa n'est pas installée @constl/ipa et obtenir versions compatibles avec serveur
    ipa_installée = ipa_est_installée(exe)
    if not ipa_installée:
        logging.info("Installation de l'IPA de Constellation")
        installer_ipa()

    # Obtenir versions ipa compatibles avec serveur
    version_ipa = obt_version_ipa(exe)
    version_ipa_désirée = obt_version_ipa_plus_récente_compatible(exe, version_ipa)

    # Installer @constl/ipa à la version la plus récente compatible avec le serveur
    if version_ipa != version_ipa_désirée:
        logging.info(f"Mise à jour de l'IPA de Constellation (courante: {version_ipa}, désirée: {version_ipa_désirée})")
        installer_ipa(version_ipa_désirée)


def ipa_est_installée(exe: TypeExe = EXE_CONSTL) -> bool:
    try:
        return _obt_version(exe, "version") is not None
    except ChildProcessError as é:
        if "ERR_MODULE_NOT_FOUND" in str(é) and PAQUET_IPA in str(é):
            return False
        else:
            raise é


def installer_ipa(version: Union[Version, SimpleSpec, str] = "latest"):
    installer_de_pnpm(PAQUET_IPA, version)


def désinstaller_constellation():
    try:
        désinstaller_ipa()
    except ConnectionError as é:
        if "This module isn't specified in a package.json file." in str(é):
            pass
        else:
            raise é
    try:
        désinstaller_serveur()
    except ConnectionError as é:
        if "This module isn't specified in a package.json file." in str(é):
            pass
        else:
            raise é


def désinstaller_ipa():
    désinstaller_de_pnpm(PAQUET_IPA)


def désinstaller_serveur():
    désinstaller_de_pnpm(PAQUET_SERVEUR)


def obt_version_ipa_plus_récente_compatible(exe: TypeExe = EXE_CONSTL, présente: Optional[Version] = None) -> Version:
    versions_disponibles = obt_versions_dispo_npm(PAQUET_IPA)
    if présente:
        versions_disponibles.append(présente)
    versions_disponibles.sort(reverse=True)

    spécifications_compatibles = SimpleSpec(_obt_version(exe, "v-constl-obli"))
    return next(v for v in versions_disponibles if v in spécifications_compatibles)


def obt_version_ipa(exe: TypeExe = EXE_CONSTL) -> Optional[Version]:
    return Version(_obt_version(exe, "v-constl"))


@lru_cache
def _vérifier_installation(exe_: Union[str, Tuple[str]]) -> True:
    message_erreur = "Constellation doit être installée et à jour sur votre appareil. " \
                     "Vous pouvez utiliser `mettre_constellation_à_jour()` pour ce faire. " \
                     "\nSi vous avez toujours des problèmes, vous pouvez utiliser `désinstaller_constellation()`" \
                     "pour nettoyer une installation brisée."

    if isinstance(exe_, tuple):
        exe_ = list(exe_)

    # Si @constl/ipa non installée, erreur
    ipa_installée = ipa_est_installée(exe_)
    if not ipa_installée:
        raise ErreurInstallationConstellation(message_erreur)
    print("ipa_installée", ipa_installée)

    # Obtenir version serveur
    version_serveur = obt_version_serveur(exe_)
    print("version_serveur", version_serveur)

    # Si serveur non installé, erreur
    if not version_serveur:
        raise ErreurInstallationConstellation(message_erreur)

    # Vérifier version @constl/serveur compatible avec client python
    if not serveur_compatible(version_serveur):
        raise ErreurInstallationConstellation(message_erreur)

    # Vérifier version @constl/ipa compatible avec @constl/serveur
    version_ipa = obt_version_ipa(exe_)
    spécifications_compatibles = SimpleSpec(_obt_version(exe_, "v-constl-obli"))
    if version_ipa not in spécifications_compatibles:
        raise ErreurInstallationConstellation(message_erreur)


def vérifier_installation_constellation(exe: TypeExe = EXE_CONSTL):
    return _vérifier_installation(exe if isinstance(exe, str) else tuple(exe))


def assurer_npm_pnpm_installés():
    version_npm = obt_version_npm()
    if not version_npm:
        logging.info("Installation de NPM")
        try:
            _installer_nodejs()
        except Exception:
            # Si on n'a pas réussi à l'installer pour vous, vous devrez le faire manuellement.
            raise FileNotFoundError("Vous devez installer Node.js au https://nodejs.org/fr/download/.")

    version_pnpm = obt_version_pnpm()
    if not version_pnpm:
        logging.info("Installation de PNPM")
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


def installer_de_pnpm(paquet: str, version: Union[Version, SimpleSpec, str] = "latest"):
    assurer_npm_pnpm_installés()
    résultat_pnpm = subprocess.run(
        ["pnpm", "add", "-g", paquet + "@" + str(version)],
        capture_output=True,
        shell=platform.system() == "Windows"
    )

    if résultat_pnpm.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation du paquet {paquet} :\n\t{résultat_pnpm.stderr.decode()}"
            f"\n\t{résultat_pnpm.stdout.decode()}"
        )


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
            sfip: Optional[Union[str, int]] = None,
            orbite: Optional[str] = None,
            exe: TypeExe = EXE_CONSTL
    ):
        soimême.port = port
        soimême.autoinstaller = autoinstaller
        soimême.exe = exe

        soimême.sfip = sfip
        soimême.orbite = orbite

        soimême.serveur: Optional[subprocess.Popen] = None

    def __enter__(soimême):
        if obtenir_contexte():
            raise ErreurConnexionContexteExistant()
        soimême.serveur, soimême.port = lancer_serveur(
            port=soimême.port,
            autoinstaller=soimême.autoinstaller,
            sfip=soimême.sfip,
            orbite=soimême.orbite,
            exe=soimême.exe
        )
        changer_contexte(soimême.port)
        return soimême

    def __exit__(soimême, *args):
        effacer_contexte()
        soimême.serveur.terminate()
