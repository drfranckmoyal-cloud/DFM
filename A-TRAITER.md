# DFM — à traiter

*Les défauts constatés et localisés, mais volontairement non corrigés. Chacun
porte ce qui a été mesuré, pour que la reprise ne recommence pas le diagnostic.*

---

## ~~1. « Voir » un autre organisme affiche l'organisme actif~~ — CORRIGÉ le 21/08/2026

Signalé par Franck, corrigé le même jour. Conservé ici pour la mémoire du défaut.

**La cause** : le lien passait bien `?id=`, mais `page_profil()` ne lisait jamais
ce paramètre — `request.args` n'y apparaissait pas une seule fois. Toutes ses
lectures portaient sur l'organisme actif.

**Ce qui a été fait**

- `profil.py` — `valeur()`, `toutes()`, `manquants()` et `verifier()` acceptent
  un organisme explicite. **Un organisme explicite coupe tout repli sur l'actif** :
  l'absence d'une valeur chez l'un est une information, pas un trou à combler
  avec celle du voisin.
- `app.py` — la route lit `?id=`, ramène à l'actif si l'identifiant est inconnu
  (un lien périmé ne casse pas un écran), et **ne bascule jamais** pour regarder.
- `profil.html` — fiche d'un autre organisme **en lecture seule** : 34 champs
  neutralisés, bandeau d'explication, et le bouton « Enregistrer » remplacé par
  « Basculer sur … ». `/profil/enregistrer` écrit sur l'organisme ACTIF sans
  savoir lequel la page affichait : neutraliser était plus sûr qu'aiguiller.

**Un défaut découvert en corrigeant** : `verifier()` cherchait les doublons en
s'excluant de l'*actif*, donc comparait Smileclub à Smileclub — *« ce SIRET est
déjà celui de Smileclub Formations »*, trois reproches absurdes sur une fiche
saine. Elle sait maintenant de qui est la fiche qu'elle examine.

**Mesuré après correction** : les deux fiches montrent 18 champs différents,
l'organisme actif reste `dsf` avant comme après consultation, et les sept écrans
qui lisent le profil répondent 200.

## ~~2, 3 et 4 — les trois points de la convention~~ — CORRIGÉS le 21/08/2026

Franck : *« peu importe fais ce qu'il faut ce sont des détails »*. Conservés ici
pour la mémoire du défaut et de sa mesure.

### Le tampon ne mordait pas sur la signature

L'intention était écrite dans le gabarit depuis le début — *« la signature doit
mordre sur le tampon, pas se ranger à côté comme deux vignettes »* — mais elle
n'était pas produite : tampon collé au bord droit, signature au bord gauche.

**Mesuré sur la page produite** : cartouche de 209 pt, signature de 83 pt,
tampon de 84 pt — et **10,6 pt de vide entre les deux**. Les pourcentages ont été
recalculés depuis ces mesures (6 % et 26 % au lieu de 8 % et 7 %) : le
recouvrement est maintenant de **24,8 pt**, vérifié sur le PDF, sur le Mac
comme sur le serveur.

### Le fond gris du tampon

Seul le tampon de DSF était concerné : **0 % de pixels transparents**, coins à
~180 de luminance, encre à 6. Celui de Smileclub était déjà détouré (90 % de
transparence) — le défaut n'était pas général.

Détouré par rampe entre 60 et 150 de luminance, plutôt qu'un seuil net qui
aurait laissé un bord en escalier autour de chaque lettre. **7 % de pixels
restent opaques** : l'impression du tampon, et rien d'autre.

**L'original est conservé** des deux côtés sous
`identite/dsf/tampon-original-avant-detourage.png`.

### La zone de cachet côté Client

Ajoutée, symétrique du tampon de l'organisme, à la même position que celui-ci
(26 %) pour que le cadre indique **exactement** où le cachet se posera. La
mention devient *« signature et cachet à apposer ici »*.

Le gabarit lit déjà `c.tampon_client` : cette donnée n'existe pas encore, mais le
jour où elle existera, l'image prendra la place du cadre sans rien changer au
gabarit. C'est là qu'OPCO Watch apposera le tampon de la structure.

### Un piège rencontré en chemin

Le tampon est une **donnée**, pas du code : `deployer.sh` ne l'emporte pas, et le
miroir du soir l'aurait écrasé par la version grise du serveur. Il a donc été
transporté séparément vers le serveur — **où vivent les données** — puis le
miroir a été rejoué. Empreintes identiques des deux côtés : `b922e8f6b1929978`.

---

## ~~6 et 7 — signature et tampon dans la fiche OF~~ — CORRIGÉS le 21/08/2026

Signalés par Franck le même jour, après la correction du point 1.

### La fiche consultée montrait les images de l'organisme actif

**Ma correction du point 1 avait manqué les deux seules images de la page.**
Tous les champs venaient du bon organisme, mais `/profil/image/<cle>` servait
toujours le fichier de l'**actif** : en consultant Smileclub depuis DSF, on
voyait la signature et le tampon de DSF sous le nom de Smileclub.

`profil.chemin_image(cle, organisme)` acceptait déjà un organisme — la route ne
le lui donnait pas. Le gabarit passe maintenant `?id={{ vu }}`, et la route
valide cet identifiant contre la liste des profils avant de s'en servir.

**Mesuré après correction**, sur le Mac et sur le serveur : quatre empreintes
distinctes.

```
signature  dsf            5a97afe00d99f289
signature  mon-organisme  e2955e5e7b3cff22
tampon     dsf            b922e8f6b1929978
tampon     mon-organisme  e9c4f7bd0d60d9d1
```

Et un audit systématique des deux fiches — 30 champs affichés de chaque côté,
comparés aux données stockées : **aucun écart**, et chaque fiche demande bien ses
propres images.

*Le logo, lui, n'était pas touché : il passe par `fiche.logo_apercu`, donc par
`charger(organisme)`, déjà corrigé au point 1.*

### En mode sombre, les deux images étaient invisibles

Signature et tampon sont de l'**encre sombre sur fond transparent**. Sur le
cartouche sombre de l'aperçu, ils disparaissaient — on croyait n'avoir rien
déposé.

L'aperçu garde désormais un fond clair en mode sombre. Ce n'est pas un
contournement : ces images seront imprimées sur du papier blanc, l'aperçu montre
donc la vérité.

**Mesuré** : page à `rgb(17, 20, 32)`, cartouches d'aperçu à `rgb(242, 244, 248)`.
La capture d'écran de cette section revient vide dans l'outil de prévisualisation
— limite de l'outil, pas de la page — la vérification s'est donc faite sur les
couleurs calculées.

---

## ~~8. Trois alertes fausses sur la fiche consultée~~ — CORRIGÉ le 21/08/2026

Signalé par Franck alors que je croyais le sujet clos. **Il avait raison : je
n'avais corrigé qu'une des deux sources.**

La fiche de Smileclub annonçait *« 3 points à corriger »* dont trois absurdes :
*« Ce SIRET est déjà celui de Smileclub Formations »*, idem IBAN et numéro de
déclaration.

### Pourquoi la première correction n'avait pas suffi

`verifier()` avait bien appris à qui appartient la fiche qu'elle examine. Mais la
page appelle **une seconde route toute seule** pendant la saisie —
`/profil/apercu` — qui :

1. charge les données de l'organisme **actif** ;
2. fusionne par-dessus les valeurs affichées à l'écran ;
3. appelle `verifier(fusion)` **sans dire de qui il s'agit**.

En consultant Smileclub depuis DSF, elle comparait donc Smileclub à Smileclub.

**Cette route est invisible dans le rendu** : rien dans le HTML ne la mentionne,
elle part d'un `setTimeout` après chaque modification. Relire le gabarit ne
pouvait pas la trouver — il fallait remonter depuis `prAfficherSoucis` jusqu'au
`fetch` qui l'alimente.

### Ce qui a été fait

- `/profil/apercu` lit un `_organisme`, le valide contre la liste des profils, et
  s'en sert pour `charger`, `verifier`, et les quatre aperçus légaux — avec
  `repli=False` dès qu'il s'agit d'un autre organisme.
- **L'aperçu ne tourne plus du tout sur une fiche consultée.** Rien n'y change :
  le faire tourner ne pouvait produire que du faux.

### Mesuré

| | Alertes |
|---|---|
| l'ancien appel, sans organisme | **4** |
| avec `_organisme=mon-organisme` | **1** |

Et sur la page réelle : le bandeau annonce *« 1 remarque »*, en gris, au lieu de
*« 3 points à corriger »* en rouge. La fiche de l'organisme actif reste
modifiable — 34 champs actifs — et son aperçu en direct fonctionne toujours.

**La remarque restante est fondée** : Smileclub porte *« en constitution »* comme
numéro de déclaration.

### La leçon

Une valeur affichée peut venir d'ailleurs que du rendu. Corriger la route qui
rend la page ne suffit pas tant qu'on n'a pas cherché **toutes** les routes que
la page interroge ensuite d'elle-même.

---

## 9. Le mail de rappel J-20 dépasse la limite de Gmail

**Trouvé le 21/08/2026** en répondant à une question de Franck sur l'emplacement
des pièces jointes.

### Le fait

| | |
|---|---|
| pièces jointes du rappel J-20 | **20,3 Mo** (3 articles + modalités d'accès) |
| une fois encodé pour le mail | **~27 Mo** — l'encodage MIME ajoute un tiers |
| limite de `smtp.gmail.com` | **25 Mo** |

Les deux organismes envoient par Gmail. **Le mail serait refusé.**

**Personne ne l'a encore vu** : le journal ne contient aucun envoi de rappel. La
mécanique n'a jamais été exercée en charge réelle.

**DFM ne contrôle pas la taille avant d'envoyer** — vérifié : aucune mention de
limite dans `mails.py`, `courrier.py` ni `envoyer_rappel.py`.

### Pourquoi ces PDF sont si lourds — mesuré

Ce ne sont pas des documents, ce sont **des images en résolution d'impression**.

```
Programme USURES.pdf       8,4 Mo   5 pages   23 Mpx   853 caracteres de texte
Programme MASTERCLASS.pdf  5,7 Mo   6 pages   35 Mpx   688 caracteres
ARTICLE LFD frontwing.pdf  7,5 Mo   6 pages   40 images jpeg a 300 dpi
05-Piskorski.pdf           6,6 Mo  12 pages   35 images jpeg, jusqu'a 412 dpi
LFD 186 focus composites   5,7 Mo   6 pages   22 images jpeg a 300 dpi
```

**300 dpi est une résolution d'imprimerie.** Pour un document lu à l'écran et
envoyé par mail, 150 dpi suffit largement — et diviser la résolution par deux
divise le poids par trois à quatre.

### Ce qui a été essayé — DEUX FOIS, ET DEUX ÉCHECS

Recompression automatique tentée le 21/08 puis le 22/08. **Aucun gain, 0 image
réduite dans les deux cas.** Le premier essai calculait la résolution depuis un
`Pixmap` intermédiaire qui rendait des dimensions fausses ; le second lisait la
largeur déclarée et n'a pourtant trouvé aucune image au-dessus du seuil, alors
que la mesure directe en montre à 300 dpi partout. La cause du second échec n'a
pas été trouvée.

**Franck a tranché le 22/08/2026 : il refait les PDF lui-même.** C'est la bonne
décision — refaire proprement vaut mieux que rafistoler, et deux tentatives
ratées suffisent.

**La cible à lui rappeler s'il la redemande :** limite Gmail 25 Mo, moins un
tiers d'encodage, soit **~18 Mo de pièces jointes** ; on est à 20,3 Mo dont
19,8 pour les trois articles. **Sous 4 Mo par article, c'est réglé.** À l'export,
choisir « qualité écran » / 150 dpi plutôt qu'imprimerie.

**Échéance mesurée le 22/08** : premier rappel J-20 le 8 octobre 2026
(Masterclass du 28/10). Puis 11 novembre pour les deux sessions du 4 décembre…
non : Usures du 04/11 → rappel le 15 octobre.

### Les deux moitiés du problème

- **Les programmes** — Franck a annoncé le 21/08/2026 qu'il **va les refaire
  prochainement**. Ne pas les recompresser : ils seront remplacés. Lui rappeler
  simplement d'exporter en qualité écran, pas en qualité imprimerie.
- **Les articles** — ce sont des publications tierces qu'il rediffuse ; il ne
  peut pas « les refaire ». **Ce sont eux qui pèsent 19,8 Mo des 20,3 Mo du
  rappel.** C'est là qu'il faut agir : recompresser, ou en envoyer moins par
  mail.

### À faire, dans l'ordre

1. **Un garde-fou à l'envoi** : refuser et le dire, plutôt que de laisser Gmail
   refuser en silence. C'est petit, et ça vaut indépendamment du reste.
2. **Recompresser les articles** à 150 dpi, avec un aperçu avant/après.
3. Rappeler la qualité d'export à Franck quand il refera les programmes.

---

## 10. Les pièces jointes ne sont dans aucune sauvegarde

`documents/_pieces` est exclu des archives quotidiennes, classé comme **cache**.

C'était vrai avant la migration : ces fichiers n'étaient que des copies de
documents vivant dans Google Drive. **Depuis la sortie de Google, ce sont les
originaux.** Le mot est resté, la réalité a changé.

Vérifié sur l'archive du 20/08 : **48 fichiers, dont zéro venant de `_pieces`**.
Restaurer depuis une archive donnerait un DFM qui tourne, mais dont les
conventions perdent leur programme et dont les rappels partent sans pièces —
sans erreur, sans message.

**Rien n'est perdu aujourd'hui** : le miroir du Mac les rapatrie chaque soir.
C'est la sauvegarde qui ne joue pas son rôle.

**Volume** : 55 Mo pour 14 pièces, mais **9 contenus distincts seulement** —
20,3 Mo occupés par cinq doublons hérités du rapatriement depuis Drive.

Les inclure telles quelles ferait passer l'archive de 4,7 Mo à ~60 Mo, soit
1,8 Go sur trente jours, pour 5,9 Go libres. **Le remède n'est donc pas
d'archiver plus, mais d'alléger la matière** — voir le point 9. Une fois les
pièces à leur poids normal, elles rentrent dans l'archive quotidienne sans
mécanisme séparé.

---

## 5. Les appels Google restants — en partie traité le 21/08/2026

**Ma note d'origine se trompait d'un facteur trente.** Elle disait « la clôture
appelle `service_sheets()` ». Mesuré : **35 routes sur 201** touchaient Google,
dont **21 appels effectifs** — 14 protégés par un `try`, **7 sans protection**.

### Ce qui a été retiré

**Huit routes ouvraient une connexion Google pour rien** : la variable était
assignée et **jamais utilisée** — vérifié par comptage des occurrences dans le
corps de chaque fonction. Comme `service_sheets()` déclenche l'authentification,
ces huit routes seraient tombées en 500 **le jour où le jeton expire**, c'est-à-
dire tous les sept jours, pour aucun bénéfice.

```
/session/<code>/cloturer              /questionnaires/relever-tout
/auto/basculer                        /session/<code>/recap/<mail>/envoyer
/session/<code>/annulation            /session/<code>/emargement/generer
/session/<code>/file-attente          /session/<code>/emargement/supprimer
```

**19 lignes retirées** — les assignations et les imports devenus orphelins.
Vérifié après coup par analyse de l'arbre syntaxique : **aucun usage orphelin**
de `sheets` ou `drive` ne subsiste, et les huit écrans principaux répondent 200.

`app.py.avant-google-mort` garde l'état précédent.

**Après : 27 routes sur 201 touchent encore Google, 13 appels effectifs.**

### Ce qui reste, et qui est un vrai chantier

Les 13 appels restants **servent** : miroir des contacts, pièces jointes de la
messagerie, logo du profil, impact d'une suppression, feuille d'émargement.
Chacun demande une décision — remplacer, retirer la fonction, ou l'accepter comme
branchement facultatif. **Ce n'est pas un détail à glisser entre deux corrections.**

Rappel de l'échéance : l'application OAuth est en mode « Test », **le jeton meurt
tous les sept jours**. Les 14 appels protégés se dégradent proprement ; les
autres méritent d'être regardés un par un.
