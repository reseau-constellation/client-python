import json
import os
import platform
import shutil
import subprocess
from typing import Optional, TypedDict, Union, List, Tuple

import urllib3
from appdirs import user_data_dir
from semantic_version import SimpleSpec, Version

from .const import V_SERVEUR_NÉCESSAIRE, PAQUET_SERVEUR, PAQUET_IPA, EXE_CONSTL

TypeExe = Union[str, List[str]]
versions_serveur_compatibles = SimpleSpec(V_SERVEUR_NÉCESSAIRE)


class ErreurInstallationConstellation(ChildProcessError):
    pass


def lancer_serveur(port=None, autoinstaller=True, exe: TypeExe = EXE_CONSTL) -> Tuple[subprocess.Popen, int]:
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


def mettre_constellation_à_jour(exe: TypeExe = EXE_CONSTL):
    print("Mise à jour de Constellation")
    assurer_npm_yarn_installés()

    try:
        vérifier_installation_constellation(exe)
    except ErreurInstallationConstellation:
        installer_tout_de_github()  # Solution temporaire à https://github.com/orbitdb/orbit-db-io/issues/39

    mettre_serveur_à_jour(exe)
    mettre_ipa_à_jour(exe)


def installer_tout_de_github():
    print("Installation de Constellation de Github")
    installer_de_github("reseau-constellation/serveur-ws")
    # installer_de_github("reseau-constellation/ipa")


def installer_de_github(paquet: str):
    print(f"Installation de {paquet} de Github")

    adresse_dossier = user_data_dir("constl-py")
    if not os.path.isdir(adresse_dossier):
        os.makedirs(adresse_dossier)

    cwd = os.path.join(adresse_dossier, paquet.split("/")[-1])
    if os.path.isdir(cwd):
        shutil.rmtree(cwd)

    résultat_git = subprocess.run(
        ["git", "clone", f"https://github.com/{paquet}.git"],
        cwd=adresse_dossier,
        capture_output=True
    )
    if résultat_git.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation de {paquet} :\n\t{résultat_git.stderr.decode()}"
        )

    print(f"\tInstallation des dépendances de {paquet}")
    résultat_installation = subprocess.run(
        ["yarn", "install"],
        cwd=cwd,
        capture_output=True
    )
    if résultat_installation.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation des dépendances de {paquet} :\n\t{résultat_installation.stderr.decode()}"
        )

    print(f"\tCompilation de {paquet}")
    résultat_compilation = subprocess.run(
        ["yarn", "compiler"],
        cwd=cwd,
        capture_output=True
    )
    if résultat_compilation.returncode != 0:
        raise ConnectionError(
            f"Erreur de compilation de {paquet} :\n\t{résultat_compilation.stderr.decode()}"
        )

    print(f"\tInstallation globale de {paquet}")
    résultat_constellation = subprocess.run(
        ["yarn", "global", "add", f"file:{cwd}"],
        cwd=cwd,
        capture_output=True
    )

    if résultat_constellation.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation du paquet {paquet} :\n\t{résultat_constellation.stderr.decode()}"
        )


def mettre_serveur_à_jour(exe: TypeExe = EXE_CONSTL):
    version_serveur = obt_version_serveur(exe)
    if not serveur_compatible(version_serveur):
        version_serveur_désirée = obt_version_serveur_plus_récente_compatible()
        print(
            f"Mise à jour du serveur Constellation (version présente: {version_serveur}; version désirée: {version_serveur_désirée})")
        installer_serveur(version_serveur_désirée)


def obt_version_serveur(exe: TypeExe = EXE_CONSTL) -> Optional[Version]:
    try:
        if v := _obt_version(exe):
            return Version(v)
    except ChildProcessError as é:
        if f"Error: Cannot find module '{PAQUET_IPA}'" in str(é):
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


def _obt_version(commande: Union[str, List[str]], arg="-v") -> Optional[str]:
    if isinstance(commande, str):
        commande = [commande]

    try:
        résultat = subprocess.run([*commande, arg], capture_output=True)
    except FileNotFoundError:
        return

    if résultat.returncode == 0:
        return résultat.stdout.decode().replace("\r", '').replace("\n", '')

    raise ChildProcessError(
        f"Erreur obtention de version pour {commande}: {résultat.stdout.decode()} {résultat.stderr.decode()}"
    )


def installer_serveur(version: Version):
    installer_de_yarn(PAQUET_SERVEUR, version)


def mettre_ipa_à_jour(exe: TypeExe = EXE_CONSTL):
    # Si @constl/ipa n'est pas installée @constl/ipa et obtenir versions compatibles avec serveur
    ipa_installée = ipa_est_installée(exe)
    if not ipa_installée:
        print("Installation de l'IPA de Constellation")
        installer_ipa()

    # Obtenir versions ipa compatibles avec serveur
    version_ipa = obt_version_ipa(exe)
    version_ipa_désirée = obt_version_ipa_plus_récente_compatible(exe, version_ipa)

    # Installer @constl/ipa à la version la plus récente compatible avec le serveur
    if version_ipa != version_ipa_désirée:
        print(f"Mise à jour de l'IPA de Constellation (courante: {version_ipa}, désirée: {version_ipa_désirée})")
        installer_ipa(version_ipa_désirée)


def ipa_est_installée(exe: TypeExe = EXE_CONSTL) -> bool:
    try:
        _obt_version(exe)
        return True
    except ChildProcessError as é:
        if f"Error: Cannot find module '{PAQUET_IPA}'" in str(é):
            return False
        else:
            raise é


def installer_ipa(version: Union[Version, SimpleSpec, str] = "latest"):
    installer_de_yarn(PAQUET_IPA, version)


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
    désinstaller_de_yarn(PAQUET_IPA)


def désinstaller_serveur():
    désinstaller_de_yarn(PAQUET_SERVEUR)


def obt_version_ipa_plus_récente_compatible(exe: TypeExe = EXE_CONSTL, présente: Optional[Version] = None) -> Version:
    versions_disponibles = obt_versions_dispo_npm(PAQUET_IPA)
    if présente:
        versions_disponibles.append(présente)
    versions_disponibles.sort(reverse=True)

    spécifications_compatibles = SimpleSpec(_obt_version(exe, "v-constl-obli"))
    return next(v for v in versions_disponibles if v in spécifications_compatibles)


def obt_version_ipa(exe: TypeExe = EXE_CONSTL) -> Optional[Version]:
    return Version(_obt_version(exe, "v-constl"))


def vérifier_installation_constellation(exe: TypeExe = EXE_CONSTL):
    message_erreur = "Constellation doit être installée et à jour sur votre appareil. " \
                     "Vous pouvez utiliser `mettre_constellation_à_jour()` pour ce faire. " \
                     "\nSi vous avez toujours des problèmes, vous pouvez utiliser `désinstaller_constellation()`" \
                     "pour nettoyer une installation brisée."

    # Si @constl/ipa non installée, erreur
    ipa_installée = ipa_est_installée(exe)
    if not ipa_installée:
        raise ErreurInstallationConstellation(message_erreur)

    # Obtenir version serveur
    version_serveur = obt_version_serveur(exe)

    # Si serveur non installé, erreur
    if not version_serveur:
        raise ErreurInstallationConstellation(message_erreur)

    # Vérifier version @constl/serveur compatible avec client python
    if not serveur_compatible(version_serveur):
        raise ErreurInstallationConstellation(message_erreur)

    # Vérifier version @constl/ipa compatible avec @constl/serveur
    version_ipa = obt_version_ipa(exe)
    spécifications_compatibles = SimpleSpec(_obt_version(exe, "v-constl-obli"))
    if version_ipa not in spécifications_compatibles:
        raise ErreurInstallationConstellation(message_erreur)


def assurer_npm_yarn_installés():
    version_npm = obt_version_npm()
    if not version_npm:
        print("Installation de NPM")
        try:
            _installer_nodejs()
        except Exception:
            # Si on n'a pas réussi à l'installer pour vous, vous devrez le faire manuellement.
            raise FileNotFoundError("Vous devez installer Node.js au https://nodejs.org/fr/download/.")

    version_yarn = obt_version_yarn()
    if not version_yarn:
        print("Installation de Yarn")
        résultat_yarn = subprocess.run(["npm", "install", "-g", "yarn"], capture_output=True)
        if résultat_yarn.returncode != 0:
            raise ConnectionError(
                f"Erreur d'installation de Yarn :\n\t{résultat_yarn.stderr.decode()}"
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
                subprocess.run(cmd.split())
            if obt_version_npm():
                return
        except FileNotFoundError:
            pass  # Si ça n'a pas fonctionné, on essayera la prochaine !

    # Système opératoire inconnu, ou bien rien n'a fonctionné
    raise OSError(système_opératoire)


def installer_de_yarn(paquet: str, version: Union[Version, SimpleSpec, str] = "latest"):
    assurer_npm_yarn_installés()
    résultat_yarn = subprocess.run(
        ["yarn", "global", "add", paquet + "@" + str(version)],
        capture_output=True
    )

    if résultat_yarn.returncode != 0:
        raise ConnectionError(
            f"Erreur d'installation du paquet {paquet} :\n\t{résultat_yarn.stderr.decode()}"
        )


def désinstaller_de_yarn(paquet):
    assurer_npm_yarn_installés()
    résultat_constellation = subprocess.run(
        ["yarn", "global", "remove", paquet],
        capture_output=True
    )

    if résultat_constellation.returncode != 0:
        raise ConnectionError(
            f"Erreur de désinstallation du paquet {paquet} :\n\t{résultat_constellation.stderr.decode()}"
        )


def obt_version_yarn() -> Optional[str]:
    return _obt_version("yarn")


def obt_version_npm() -> Optional[str]:
    return _obt_version("npm", "version")


class Serveur(object):
    def __init__(soimême, port: Optional[int] = None, autoinstaller=True, exe: TypeExe = EXE_CONSTL):
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
