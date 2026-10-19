# Les polices et les icônes de DFM

Depuis le 18 octobre 2026, **DFM ne va plus chercher ses polices chez
personne**. Tout est dans `static/`, servi par DFM, gardé un an par le
navigateur.

## Pourquoi on a fait ça

Chaque page attendait deux services extérieurs avant de s'afficher :

| | Avant | Après |
|---|---|---|
| Feuille de style des icônes | 218 Ko chez jsdelivr, bloquante | **3 Ko** chez nous |
| Police d'icônes | 809 Ko, 5 268 icônes | **37 Ko**, les 204 employées |
| Police de texte (Inter) | chez Google, revérifiée chaque jour | **48 Ko** chez nous, une fois |
| Bibliothèques QR code et ZIP | chez cdnjs | chez nous |

Un service extérieur lent ou indisponible figeait l'affichage. Plus
maintenant : plus aucun tiers n'est sur le chemin d'une page.

## Le jour où tu ajoutes une icône

Une icône employée mais absente de notre police **n'affiche rien, en
silence**. Deux noms inexistants ont vécu des mois dans DFM sans que personne
le voie. Donc, après avoir ajouté une icône quelque part :

```bash
cd ~/Desktop/Claude-Projects/DFM && venv/bin/python fabriquer_polices.py
```

L'outil recense les icônes employées partout — gabarits, JavaScript, Python —
refabrique la police et la feuille de style, et **nomme à la fin celles qui
n'existent pas**. S'il en nomme une, c'est une faute de frappe dans le nom :
va voir sur https://tabler.io/icons comment elle s'appelle vraiment.

Il lui faut un outil qui n'est pas installé sur le serveur, seulement sur le
Mac :

```bash
cd ~/Desktop/Claude-Projects/DFM && venv/bin/pip install fonttools brotli
```

Ensuite, `./deployer.sh` comme d'habitude.

## Ce qu'il ne faut pas faire

- **Ne pas modifier `static/polices.css` à la main** : il est fabriqué, et la
  prochaine fabrication écrasera la modification.
- **Ne pas changer le nom d'un fichier de `static/`** sans refaire pointer
  `base.html` dessus : son adresse porte une empreinte de son contenu
  (`?v=...`), posée par `app.statique()`.

## Les licences

Les deux polices autorisent cet hébergement : **Inter** est sous SIL Open Font
1.1, **Tabler Icons** sous MIT. Les mentions sont dans l'en-tête de
`static/polices.css`.
