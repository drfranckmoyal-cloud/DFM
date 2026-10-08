# Fiche de retour en arrière — migration Python

> À garder sous la main pendant toute la migration.
> Écrite le 02/08/2026, **avant** que quoi que ce soit ne soit modifié.
> Chaque commande se copie-colle telle quelle dans le Terminal, puis Entrée.

---

## D'abord : la règle qui vous protège

> **CORRECTIF du 02/08/2026, après l'installation.** L'installateur python.org a
> modifié ce à quoi répond la commande `python3` : elle désigne désormais 3.13,
> et non plus le Python d'Apple. La commande habituelle
> `cd ~/Desktop/DFM && python3 app.py` **ne fonctionne donc plus pour l'instant**
> (message `ModuleNotFoundError: No module named 'flask'`).
> Le Python d'Apple et ses bibliothèques sont **intacts** : il faut simplement
> le désigner par son chemin complet, `/usr/bin/python3`. Toutes les commandes
> de repli ci-dessous ont été corrigées en ce sens et retestées.

**Votre filet permanent, qui fonctionne quoi qu'il arrive :**

```
cd ~/Desktop/DFM && /usr/bin/python3 app.py
```

`/usr/bin/python3` est le Python d'Apple, en 3.9.6, avec toutes les
bibliothèques de DFM. Nous n'y touchons pas, et rien ne peut le remplacer.

Si vous ne savez plus où vous en êtes : tapez cette commande. DFM démarre
comme avant.

---

## Vos données ne sont jamais en jeu

Aucune étape de la migration ne lit, ne déplace ni ne réécrit :

- `credentials.json` et `token.json` — vos accès Google
- `formations.json`, `sessions.json`, `parametres.json`, `bibliotheque.json`, `mails.json`
- le dossier `profils/`, le dossier `questionnaires_figes/`
- vos sauvegardes `.avant-*`
- **rien dans Google Sheets, Drive ou Supabase**

Nous n'ajoutons que deux choses : un Python supplémentaire dans un dossier système
à lui, et un dossier `venv` à l'intérieur de DFM.

---

## Retour n° 1 — « Je veux juste que DFM redémarre »

Le plus simple, et il marche toujours.

Dans le Terminal :

```
cd ~/Desktop/DFM && /usr/bin/python3 app.py
```

Puis ouvrez `http://127.0.0.1:5001` dans le navigateur.

Pour arrêter DFM : cliquez dans la fenêtre du Terminal et faites **Ctrl + C**.

---

## Le lanceur `DFM.command`

Double-cliquez **« Lancer DFM »** sur le Bureau, ou `DFM.command` dans le dossier.
Il choisit tout seul :

- l'environnement isolé `venv` s'il existe (Python 3.13) ;
- **sinon** le Python d'Apple, `/usr/bin/python3` (3.9.6), qui fonctionne toujours.

Il affiche en clair quelle version il utilise. Le navigateur s'ouvre seul après
trois secondes.

Ce lanceur ne peut pas vous bloquer : même si vous supprimez `venv`, il bascule
tout seul sur le Python d'Apple.

### Arrêter DFM

**La bonne façon : Ctrl + C** dans la fenêtre du Terminal. Le serveur s'arrête
proprement et le port se libère.

### Si vous fermez la fenêtre par mégarde

Rien de grave, **aucune donnée n'est perdue** : DFM ne garde rien en mémoire,
tout est écrit au fur et à mesure dans Google Sheets et dans les fichiers du
dossier.

Mais attention à un détail : fermer la fenêtre n'arrête pas toujours le serveur.
Un processus peut continuer en arrière-plan et garder le port 5001 occupé.
Vous vous en apercevrez ainsi :

- le navigateur affiche encore DFM sur `http://127.0.0.1:5001` — c'est le
  serveur oublié qui répond ;
- ou un nouveau lancement échouerait avec « Address already in use ».

**La solution : relancez simplement le lanceur.** Il détecte la situation tout
seul et vous propose :

```
  Un DFM tourne deja sur le port 5001.

  [1] L'arreter et en demarrer un neuf   (recommande)
  [2] Le garder et juste ouvrir le navigateur
  [3] Ne rien faire et fermer
```

Tapez **1** dans la quasi-totalité des cas. Vous n'avez jamais besoin de savoir
ce qu'est un processus ni d'ouvrir le Terminal vous-même.

### Mettre le lanceur à portée de main

- **Sur le Bureau** : c'est déjà fait, le raccourci s'appelle **« Lancer DFM »**.
  Si vous le supprimez, refaites-en un : ouvrez le dossier DFM, cliquez sur
  `DFM.command` en maintenant **Ctrl**, choisissez **Créer un alias**, puis
  glissez l'alias sur le Bureau.
- **Dans le Dock** : glissez « Lancer DFM » dans la partie **droite** du Dock,
  celle qui se trouve après la ligne de séparation, près de la Corbeille. La
  partie gauche est réservée aux applications et refusera le fichier.

---

## Retour n° 2 — « Le nouvel environnement pose problème »

Le dossier `venv` contient uniquement des bibliothèques. **Aucune donnée.**
Le supprimer ne fait perdre que du temps de réinstallation.

```
cd ~/Desktop/DFM && rm -rf venv
```

Puis retour n° 1 pour redémarrer.

Si vous avez un lanceur `DFM.command` et qu'il ne fonctionne plus après ça :
c'est normal, il pointait vers `venv`. Utilisez le retour n° 1 en attendant.

---

## Retour n° 3 — « Je veux retirer complètement le nouveau Python »

> Version installée : **Python 3.13.14** (fichier `python-3.13.14-macos11.pkg`).
> Le dossier système porte le numéro de série `3.13`, sans le dernier chiffre.

À faire seulement si vous voulez que le Mac retrouve exactement sa configuration
d'avant. Ces deux commandes demandent **votre mot de passe** (il ne s'affiche pas
quand vous le tapez, c'est normal).

```
sudo rm -rf /Library/Frameworks/Python.framework/Versions/3.13
```

```
sudo rm -rf "/Applications/Python 3.13"
```

Ensuite, vérifiez que le Python d'Apple répond toujours :

```
python3 -V
```

Vous devez lire `Python 3.9.6`.

---

## Retour n° 4 — « Un fichier de DFM a été modifié et je veux l'ancien »

Chaque fichier touché pendant l'audit a une copie de sauvegarde nommée
`<fichier>.avant-<point>`. Pour restaurer, par exemple, `app.py` :

```
cd ~/Desktop/DFM && cp app.py.avant-C8 app.py
```

Pour voir toutes les sauvegardes disponibles d'un fichier :

```
cd ~/Desktop/DFM && ls -la app.py.avant-*
```

La migration Python **ne modifie aucun fichier de code** — ce retour ne devrait
pas servir, il est là par principe.

---

## Comment savoir sur quel Python je tourne

```
/usr/bin/python3 -V
```
→ doit toujours afficher `Python 3.9.6`. C'est le Python d'Apple, votre filet.

```
python3 -V
```
→ affiche `Python 3.13.14` depuis l'installation. C'est normal : la commande
courte désigne maintenant le nouveau Python.

Et pour savoir si l'environnement isolé existe :

```
ls ~/Desktop/DFM/venv/bin/python
```

- un chemin s'affiche → il existe.
- `No such file or directory` → il n'existe pas, vous êtes sur l'état d'origine.

---

## Si DFM ne démarre plus du tout

1. Fermez toutes les fenêtres du Terminal.
2. Ouvrez-en une nouvelle.
3. Tapez : `cd ~/Desktop/DFM && /usr/bin/python3 app.py`
4. Si un message d'erreur apparaît : **ne tapez rien d'autre**, copiez le message
   entier et transmettez-le. Ne relancez pas d'installation à l'aveugle.

Si le message parle d'un module introuvable (`ModuleNotFoundError`), les
bibliothèques de Python 3.9 sont intactes dans
`~/Library/Python/3.9/lib/python/site-packages` — elles peuvent être réinstallées
depuis `requirements.txt` :

```
cd ~/Desktop/DFM && /usr/bin/python3 -m pip install --user -r requirements.txt
```

---

## Ce que vous ne devez jamais faire

- **Ne supprimez pas** `/Library/Developer/CommandLineTools` — c'est le Python
  d'Apple, votre filet.
- **Ne lancez pas** `sudo pip install` : cela écrirait dans le Python système.
- **Ne supprimez pas** `credentials.json` ni `token.json` : ils ne sont pas
  régénérables sans repasser par la console Google.
- **Ne supprimez pas** les fichiers `.avant-*`.

---

## Points de contrôle : « tout va bien » se vérifie ainsi

Après n'importe quelle étape, ces trois commandes disent si DFM est sain.
Aucune n'envoie de mail ni ne modifie de donnée.

```
cd ~/Desktop/DFM && /usr/bin/python3 -c "import app; print(len(list(app.app.url_map.iter_rules())), 'routes')"
```
→ doit afficher `105 routes`

```
cd ~/Desktop/DFM && /usr/bin/python3 -c "from connexion import service_sheets; service_sheets(); print('Google OK')"
```
→ doit afficher `Google OK` **sans ouvrir de fenêtre de navigateur**

```
cd ~/Desktop/DFM && /usr/bin/python3 app.py
```
→ doit démarrer et servir `http://127.0.0.1:5001`
