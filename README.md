# ConstellationPy

Cette librarie offre un client [Constellation](https://reseau-constellation.github.io/constellation)
pour Python. Elle fonctionne en lançant
un [serveur ws Constellation](https://github.com/reseau-constellation/serveur-ws)
local, avec lequel elle gère ensuite la communication par websocket.

## Installation

Vous pouvez installer ConstellationPy avec `poetry` :

`poetry add constellationPy`

...ou bien avec `pip`

`pip install constellationPy`

Si le serveur Constellation n'est pas déjà installé sur votre machine, ConstellationPy l'installera automatiquement pour
vous. Pour ce faire, vous devrez au tout minimum avoir [Node.js](https://nodejs.org/fr/)
installé localement.

## Utilisation

ConstellationPy est une librarie **asyncrone** basée sur [trio](https://trio.readthedocs.io). Étant donné que le serveur
Constellation est fondamentallement asyncrone aussi, c'était la décision naturelle.

Cependant, nous comprenons bien que la grande majorité des utilisatrices et utilisateurs de Python n'ont aucune idée de
ce qu'est la programmation asyncrone, ni aucun goût ou raison de l'apprendre. C'est pour cela que ConstellationPy vous
offre également un IPA syncrone.

Attention ! L'IPA syncrone fonctionne bien pour des petites tâches (p. ex., récupérer un ou deux jeux de données), mais
l'IPA asyncrone est beaucoup plus efficace si vous traitez de grands nombre de données ou de requètes à Constellation.
Si vous avez besoin d'accéder beaucoup de différentes bases de données Constellation, peut-être que ça vaudrait la
peine, après tout,
[d'apprendre](https://trio.readthedocs.io/en/stable/tutorial.html) comment utiliser ces drôles de `async` et `await` en
Python.

### IPA syncrone

En premier lieu, nous devons lancer le serveur Constellation. C'est absolument nécessaire, à moins que vous n'aviez déjà
lancé un serveur Constellation
[manuellement](https://github.com/reseau-constellation/serveur-ws/blob/master/README.md#ligne-de-commande), lorsque, par
exemple, vous voulez exécuter plusieurs codes Python qui utilisent Constellaltion en parallèle sans dupliquer le
serveur (oui, c'est bien possible) !

Donc, on commence. La façon la plus sure, c'est d'utiliser un bloc `with`, car celui-ci fermera automatiquement le
serveur une fois que vous aurez terminé avec. **Cette syntaxe permettra aussi au client Constellation de détecter
automatiquement le port auquel il devra se connecter.**

```python
from constellationPy import Serveur, ClientSync

with Serveur():
    client = ClientSync()
    données = client.appelerUneFonction()
    ...

```

Si vous avez déjà lancé votre propre serveur Constellation, vous devrez spécifier le port manuellement dans le client :

```python
from constellationPy import ClientSync

client = ClientSync(port=5001)
...

```

### Fonctions disponibles

Toutes les fonctions de l'[ipa Constellation](https://github.com/reseau-constellation/ipa) sont disponibles. Bon,
quasiment toutes. Pour être précis, toute fonction qui prend, au maximum, un argument qui est lui-même une fonction.

*Note : vous pouvez appeler les fonctions Constellation en forme kebab (`ma_fonction`, style Python)
ou bien chameau (`maFonction`, style JavaScript)*. À titre d'exemple :

```python
from constellationPy import ClientSync, Serveur

with Serveur():
    client = ClientSync()

    résultatChameau = client.obtIdOrbite()
    résultat_kebab = client.obt_id_orbite()

    print(résultatChameau == résultat_kebab)
```

Vous pouvez également accéder les sous-objets de Constellation (`compte`, `bds`, `tableaux`, et ainsi de suite) :

```python
from constellationPy import ClientSync, Serveur

with Serveur():
    client = ClientSync()

    client.compte.sauvegarderNom("fr", "moi !")
    client.bds.créerBd("ODbl-1.0")

```

**Quelques points importants**

* Les fonctions plus obscures qui prennent plus qu'une autre fonction comme argument (p.
  ex. `client.suivreBdDeFonction`) ne fonctionnent pas avec le client Python. Ne vous en faites pas. Elles sont obscures
  pour une raison. Vous avez amplement de quoi vous occuper avec le reste de l'IPA !
* Avec le client syncrone, les fonctions du suivi (voir ci-dessous) doivent être appellées avec une fonction vide (p.
  ex., `lambda: pass`) à la place de la fonction de suivi.

#### Fonctions de suivi

Constellation, dans sa version asyncrone JavaScript, offre des fonctions qui, plutôt que de rendre le résultat
immédiatement, *suivent* le résultat à travers le temps et vous notifient (selon une fonction que vous choisissez)
chaque fois que le résultat change. La grande majorité des fonctions utiles de l'IPA de Constellation (p.
ex., `client.tableaux.suivreDonnées`) sont de ce genre.

Évidemment, ce comportement n'est pas util dans un programme syncrone. Le client syncrone `ClientSync`
s'occupe donc de vous rendre le résultat, sans tracas. Il vous suffira de passer une fonction vide là où la fonction
originale s'attendait à avoir la fonction de suivi. Par exemple, si l'on appellerait la fonction comme suit dans
Constellation JavaScript,

```javascript
const données = await client.tableaux.suivreDonnées(idTableau, fSuivi)
```

Ici, en Python, nous ferons ainsi :

```python
from constellationPy import ClientSync, Serveur, fais_rien

idTableau = "/orbitdb/zdpu..."
with Serveur():
    client = ClientSync()

    mes_données = client.tableaux.suivreDonnées(idTableau, fais_rien)

```

### IPA asyncrone

```python
from constellationPy import Serveur, ouvrir_client

with Serveur():
    async with ouvrir_client() as client:
        données = await client.appelerUneFonction()
        ...

```

#### Fonctions de suivi et `une_fois`

Tel que mentionné ci-dessus, la majorité des fonctions utiles de Constellation sont des fonctions de suivi.
Nous devons les appeler avec une fonction qui sera invoquée à chaque fois que le résultat sera mis à jour.
```python
import trio
from constellationPy import Serveur, ouvrir_client

idTableau = "/orbitdb/zdpu..."
with Serveur():
    async with ouvrir_client() as client:
        # Suivre les données du réseau pour 15 secondes, et imprimer les résultats au fur et à mesure
        # qu'ils nous parviennent du réseau
        oublier_données = await client.tableaux.suivreDonnées(idTableau, print)
        trio.sleep(15)

        oublier_données()  # Maintenant on ne recevra plus les mises à jour des données

```

Mais en Python, il est probable que, au lieu de vouloir suivre le résultat de la fonction à travers le temps, vous préférerez
obtenir les données présentes et puis poursuivre vos analyses. La fonction `une_fois`
vous permet de faire justement celà :

```python
from constellationPy import Serveur, ouvrir_client, une_fois

idTableau = "/orbitdb/zdpu..."
with Serveur():
    async with ouvrir_client() as client:
        async def f_données(f):
            return await client.tableaux.suivreDonnées(idTableau, f)
        
        données = await une_fois(f_données, client)
        
        print(données)

```

#### Utilisation avancée

Voici un exemple un peu plus avancé. Si vous avez plusieurs coroutines Python que vous voulez exécuter en parallèle avec
Constellation, vous pouvez créer une pouponnière `trio` et la réutiliser pour les deux coroutines en invoquant `Client`
directement.

```python
import trio
from constellationPy import Client

résultats = {}


async def coroutine1(client):
    données = await client.appelerUneFonction()
    résultats["1"] = données


async def coroutine2(client):
    données = await client.appelerUneFonction()
    résultats["2"] = données


async def principale():
    async with trio.open_nursery() as pouponnière:
        async with Client(pouponnière) as client:
            await client.connecter()  # À ne pas oublier ! Sinon je ne suis pas responsable.

            pouponnière.start_soon(coroutine1, client)
            pouponnière.start_soon(coroutine2, client)


trio.run(principale)

print(résultats)
```

Ceci peut aussi être utile avec
les [canaux](https://trio.readthedocs.io/en/stable/reference-core.html#using-channels-to-pass-values-between-tasks)
de `trio` pour communiquer entre les coroutines :

```python
import trio
from constellationPy import Client


async def coroutine_constellation(pouponnière, canal_envoie):
    async with Client(pouponnière) as client:
        await client.connecter()  # À ne pas oublier ! Sinon je ne suis pas responsable.

        données = await client.appelerUneFonction()

        async with canal_envoie:
            await canal_envoie.send(données)


async def une_autre_coroutine(canal_réception):
    async with canal_réception:
        async for message in canal_réception:
            print(message)  # En réalité, faire quelque chose d'asyncrone, comme écrire au disque


async def principale():
    async with trio.open_nursery() as pouponnière:
        canal_envoie, canal_réception = trio.open_memory_channel(0)

        pouponnière.start_soon(coroutine_constellation, pouponnière, canal_envoie)
        pouponnière.start_soon(une_autre_coroutine, canal_réception)


trio.run(principale)
```
