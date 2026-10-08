# CHANTIER — faire de DFM un logiciel livrable à d'autres

*Note technique. Écrite le 8 octobre 2026, à partir de mesures prises ce jour-là
sur l'installation en service. Elle ne traite que du logiciel : ce qu'il faut
changer dans DFM pour qu'il puisse tourner chez quelqu'un d'autre que nous.*

---

## 1. D'où on part

Mesuré le 8 octobre 2026 :

| | |
|---|---|
| Code | **48 000 lignes** — 29 000 de Python (94 modules), 19 000 de gabarits |
| Écrans | **49** |
| En service | deux organismes cloisonnés, en production depuis juin 2026 |
| Données | 75 Mo de documents, base de 320 Ko, **un seul serveur**, disque à 82 % |
| Tests | **un seul fichier** |
| Dépôt git | créé le 8 octobre 2026 |

Deux choses sont déjà acquises, et ce sont les deux plus difficiles :

- **La chaîne Qualiopi est complète et prouvée** — convention, signature
  électronique, facture, émargement, attestation, questionnaires — avec un
  **journal scellé par chaînage** qui en garde la trace. C'est ce qu'un
  auditeur demande, et ça ne s'invente pas depuis un cahier des charges.
- **L'identité de l'organisme est déjà un paramètre** : SIRET, numéro de
  déclaration, adresse, IBAN, logo, signature, expéditeur des mails. Le
  cloisonnement entre Smileclub et DSF a réglé ça en août. Un troisième
  organisme n'exige aucune modification de code.

---

## 2. La décision d'architecture : une installation par client

Le code suppose **une** installation. Les sessions sont chargées en mémoire au
démarrage, une session est active à un instant donné, la configuration vit dans
des fichiers JSON globaux, la base est un fichier SQLite. Faire cohabiter
plusieurs clients dans une seule instance demanderait de réécrire le cœur.

**Une installation par client** — un serveur, une base, un domaine chacun —
c'est ce que le code sait faire aujourd'hui, presque sans y toucher. Avec un
script d'installation, ça tient jusqu'à vingt ou trente clients.

> **Conséquence pour tout ce qui suit :** aucun des chantiers ci-dessous ne
> cherche à rendre DFM multi-client. Ils cherchent à rendre **une** installation
> livrable, sûre, et maintenable à distance. Le multi-client ne se décide qu'une
> fois qu'il y a des installations à maintenir.

---

## 3. Les chantiers, dans l'ordre où ils se débloquent

### 3.1 Comptes, utilisateurs et rôles — *bloquant*

**Aujourd'hui :** un seul mot de passe pour toute l'application (`acces.py`).
Pas d'utilisateurs, pas de rôles. Le journal dit « DFM a fait », jamais
« untel a fait ».

**À faire :** une table d'utilisateurs, un mot de passe haché par personne, deux
rôles suffisent au départ (gérant / assistante), l'auteur inscrit dans chaque
entrée du journal, et un écran de gestion des comptes.

**Pourquoi en premier :** ça touche le journal, donc la preuve d'audit. Chaque
semaine d'attente ajoute des entrées sans auteur, qu'on ne pourra jamais
attribuer après coup.

### 3.2 Sauvegarde et restauration — *bloquant*

**Aujourd'hui :** 75 Mo de conventions signées, factures et attestations sur un
serveur unique, disque rempli à 82 %, et le miroir vers le Mac ne fonctionne
plus depuis des semaines.

**À faire :** une sauvegarde quotidienne chiffrée vers un stockage objet
européen, couvrant `documents/`, la base et la configuration — **et une
restauration réellement testée**. Une sauvegarde qu'on n'a jamais restaurée
n'est pas une sauvegarde. Agrandir le disque, ou sortir `documents/` sur un
stockage dédié.

**Pourquoi :** perdre ses conventions signées, pour un organisme, c'est perdre
sa certification.

### 3.3 L'envoi des mails — *bloquant dès le deuxième client*

**Aujourd'hui :** Scaleway bloque le SMTP ; le repli passe par l'API Gmail avec
un verrou d'identité par organisme, et l'autorisation Google meurt tous les sept
jours tant que l'application reste en mode « Test ».

**À faire :** un service d'envoi transactionnel en HTTPS, un expéditeur par
organisme, SPF et DKIM sur le domaine du client.

**Point d'appui :** `courrier.py` est déjà le **seul** point de passage de tout
envoi. Le changement se fait là, et nulle part ailleurs.

### 3.4 Une installation reproductible

**Aujourd'hui :** le serveur a été monté à la main, étape par étape.

**À faire :** un script qui, depuis une machine nue, installe Python et le venv,
nginx et le certificat, le service systemd, crée une base vide et pose le mot de
passe. Et `remise_a_zero.py` remis en état : il est périmé et casserait DFM s'il
était lancé aujourd'hui.

**Critère de réussite :** monter une installation neuve en moins d'une heure,
sans intervention manuelle.

### 3.5 Le filet : des tests là où une erreur coûte cher

**Aujourd'hui :** un seul fichier de test. Tant que DFM est notre outil, un
retour arrière se fait avec les fichiers `.avant-`. Dès qu'il tourne chez trois
clients, une correction qui casse un écran casse chez trois clients à la fois.

**À faire :** pas une couverture complète — les cinq points où une erreur ne se
voit pas tout de suite et coûte cher : le chaînage du journal, le calcul des
statuts, la numérotation des factures, le cloisonnement entre organismes, la
génération de la convention. Lancés avant chaque envoi vers un client.

### 3.6 Ce qui reste écrit en dur

L'identité est déjà paramétrée (§1). Ce qui reste à sortir du code :

- les **modèles de mails et de documents** vivent dans le dépôt, pas chez le
  client : deux clients ne pourront pas avoir des textes différents ;
- les gabarits du **site public** portent encore des formulations propres à nos
  organismes ;
- les **catégories de documents** sont figées dans `documents.py`.

### 3.7 RGPD, côté technique

Livrer DFM à un tiers nous fait passer de responsable de nos données à
**sous-traitant** des siennes. Techniquement, cela demande :

- un **export complet** d'une installation — un client doit pouvoir partir avec
  ses données, sans nous ;
- l'**effacement** sur demande d'un apprenant, sans casser le chaînage du
  journal (effacer la donnée, garder la preuve de l'action) ;
- les **durées de conservation** appliquées automatiquement — `conservation.py`
  existe déjà, il reste à le brancher.

### 3.8 Savoir qu'une installation est en panne avant le client

**Aujourd'hui :** les pannes se découvrent en ouvrant l'écran. L'alerte du
traitement, par exemple, n'est lue que par celui qui regarde.

**À faire :** une sonde qui vérifie chaque installation — la page répond, le
traitement est passé aujourd'hui, le disque n'est pas plein, la sauvegarde date
de moins de 24 h — et prévient.

---

## 4. Ce qu'il ne faut pas faire

- **Ne pas réécrire.** 48 000 lignes qui tournent en production et qui ont
  passé un audit valent plus que n'importe quelle architecture propre sur le
  papier. Tout ce qui précède se fait *dans* le code existant.
- **Ne pas viser le multi-client d'emblée.** C'est la décision qui coûte le plus
  cher et qu'on peut prendre le plus tard.
- **Ne rien livrer à un tiers** avant que 3.1, 3.2 et 3.3 soient faits. Ce ne
  sont pas des améliorations, ce sont les conditions pour que le logiciel soit
  confiable chez quelqu'un d'autre.

---

## 5. Ordre de marche

| Palier | Chantiers | Ce qu'il débloque |
|---|---|---|
| **0 — sûreté** | dépôt git ✅ · comptes (3.1) · sauvegarde (3.2) · tests (3.5) | On peut corriger sans casser, et on ne perd rien |
| **1 — livrable** | mails (3.3) · installation (3.4) · paramétrage (3.6) | Une installation peut être montée chez un tiers |
| **2 — tenable** | RGPD (3.7) · supervision (3.8) | Plusieurs installations peuvent être maintenues |

Le palier 0 ne se voit pas à l'écran : rien n'y change pour l'utilisateur. C'est
pourtant le seul qui conditionne tous les autres.
