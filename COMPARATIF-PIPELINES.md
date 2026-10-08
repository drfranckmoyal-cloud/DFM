# Les deux pipelines, comparés

*Relevé dans le code le 23/08/2026, en vue de décider s'il faut deux créateurs de
formation distincts. Rien ici n'est déduit d'un nom d'étape : chaque abstention
a été trouvée dans le code qui la prononce.*

---

## Le fait qui commande tout

Le pipeline compte **18 étapes**, dans une seule liste (`dfm.py`, `ETAPES`).

| | |
|---|---|
| étapes qui **s'abstiennent en mode client** | **11** |
| étapes qui **s'abstiennent en mode individuel** | **5** |
| étape qui ne sert qu'en individuel, sans le dire (absence de formulaire) | **1** |
| **étapes réellement communes aux deux** | **1** |

> **Sur dix-huit étapes, une seule est commune : la génération des attestations.**

Les deux parcours ne se ressemblent pas — ils se croisent une fois, à la fin.

---

## Le détail, étape par étape

| # | Étape | Individuel | Client |
|---|---|:---:|:---:|
| 1 | Import des inscriptions *(formulaire Google)* | ● | — |
| 2 | Demandes du formulaire *(page publique)* | ● | — ¹ |
| 3 | Relevé des annulations | ● | — |
| 4 | Mails de file d'attente | ● | — |
| 5 | **Convention client** | — | ● |
| 6 | **Envoi de la convention au client** | — | ● |
| 7 | **Relevé de la signature du client** | — | ● |
| 8 | **Facture client** | — | ● |
| 9 | **Convention contresignée + facture** | — | ● |
| 10 | Préparation des conventions à signer | ● | — |
| 11 | Envoi des mails de signature | ● | — |
| 12 | Relevé des signatures | ● | — |
| 13 | Génération des conventions signées | ● | — |
| 14 | Envoi des mails de confirmation | ● | — |
| 15 | Envoi des rappels J-20 | ● | — |
| 16 | Génération des factures | ● | — |
| 17 | Envoi des factures | ● | — |
| 18 | **Génération des attestations** | ● | ● |

¹ *Pas d'abstention écrite : une session client n'est simplement jamais publiée
sur la page d'inscription. `inscription.py` la refuse explicitement — « ses
participants sont saisis par le centre, elle n'a pas de formulaire public ».*

---

## Ce qui change vraiment, et pourquoi

### Qui signe

**Individuel** : chaque praticien signe sa propre convention, en ligne, une par
personne. DFM prépare, envoie, relève, contresigne — quatre étapes par inscrit.

**Client** : **une seule convention**, signée par le représentant légal du
centre, qui liste tous les participants. Une signature pour six praticiens.

### Qui paie

**Individuel** : une facture par praticien, un règlement par praticien, une
relance par praticien.

**Client** : **une facture unique** au nom du centre. Le praticien ne doit rien
et ne reçoit ni facture ni relance — c'est précisément ce que dit l'abstention de
l'étape 17 : *« la facture part au client, pas à chaque praticien »*.

### D'où viennent les participants

**Individuel** : ils s'inscrivent eux-mêmes sur la page publique. DFM les relève.

**Client** : **vous les saisissez**, en collant la liste que le centre vous
envoie. Aucun formulaire, aucune file d'attente, aucune annulation individuelle.

### Ce qui reste commun

Les **attestations** — parce qu'elles sont nominatives dans les deux cas. Et,
hors pipeline, les **questionnaires** d'évaluation, de satisfaction et à froid,
qui suivent l'apprenant quel que soit le payeur.

---

## Ce que la fiche de formation demande aujourd'hui

L'écran de création réclame **21 champs**. Voici ce qu'ils deviennent selon le
type.

### Servent aux deux (13)

`nom_formation` · `titre_complet` · `description` · `objectifs` · `public`
`duree_heures` · `horaires` · `adresse` · `couleur` · `tarif`
`programme_id` · `acces_id` · `modele_evaluation`

### Ne serviront **jamais** à une formation client (6)

| Champ | Pourquoi il ne sert pas |
|---|---|
| `modele_mail_signature` | le praticien ne reçoit pas ce mail — seul le représentant signe |
| `modele_mail_confirmation` | ce mail porte la convention individuelle et le RIB du praticien |
| `pieces_rappel` | le rappel J-20 s'abstient en mode client |
| `places_max` | la taille de la session, c'est la liste que le centre envoie |
| `descriptif_inscription` | il n'y a pas de page d'inscription |
| `code_edition` | idem |

### Servent aux deux, mais pas de la même façon (2)

`modele_satisfaction` et `modele_froid` — communs, mais les questionnaires d'une
session client s'adressent à des salariés d'un même centre, pas à des praticiens
venus de partout.

### Champs qui n'existent **que** pour le client

**Aucun.** Ce qui distingue une session client vit sur la **session** (le client,
les participants) et sur la **fiche du client**, pas sur la formation.

---

## Ce que ça donne comme réponse

**Un créateur distinct se justifie — mais pas pour la raison qu'on croit.**

Ce n'est pas qu'une formation client demanderait d'autres champs : elle en
demande **six de moins**, et pas un de plus.

Six champs qui ne serviront jamais, ce sont six occasions d'hésiter, de remplir
quelque chose d'inutile, et surtout de **croire que ça marchera** — de joindre
des articles au rappel J-20 en pensant qu'ils partiront, alors que l'étape
s'abstient.

**Et il y a une raison plus forte, qui elle est propre au client.** Franck a
décidé le 21/08/2026 que *« les tarifs des formations client seront calibrés sur
les barèmes OPCO »*. Le champ `tarif` d'une formation client n'est donc pas un
prix libre : c'est un montant contraint, dont dépend le financement du centre.
Un écran qui le dirait — voire qui afficherait le barème à côté — vaudrait mieux
qu'un champ nu identique à celui d'une formation individuelle.

> **La différence n'est pas dans les champs. Elle est dans ce qu'il faut
> expliquer au moment de les remplir.**

---

## Trois façons de le faire

| | Ce que ça donne | Ce que ça coûte |
|---|---|---|
| **Deux écrans séparés** | chacun ne montre que ce qui sert, avec ses propres explications | deux gabarits à tenir en parallèle ; une correction à faire deux fois |
| **Un écran, un choix en tête** | on choisit le type d'abord, l'écran s'adapte | un seul gabarit, mais des conditions partout dedans |
| **Un écran, six champs repliés** | les champs individuels se replient si le type est « client » | le plus petit changement — mais l'écran reste un compromis |

*À trancher par Franck. Le comparatif ci-dessus lui donne de quoi choisir ; il
ne choisit pas à sa place.*

---

## Une question que ce comparatif soulève et ne tranche pas

**Aujourd'hui, le type se décide à la création de la SESSION, pas de la
FORMATION.** Une même formation peut donc servir en individuel et en client.

Si une formation devient « client » à la création, faut-il :

- **l'y contraindre** — une formation client ne peut plus donner de session
  individuelle ?
- **ou seulement le proposer par défaut** — la session peut encore choisir ?

C'est une vraie question de conception : la première voie est plus claire, la
seconde plus souple. Elle mérite d'être posée avant de coder quoi que ce soit.
