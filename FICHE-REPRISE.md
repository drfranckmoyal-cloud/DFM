# DFM — Fiche de reprise

*Écrite le 19/08/2026. Destinée au développeur qui intègre DFM à une suite logicielle,
et à Claude Code qui l'assistera. Chaque affirmation ici a été mesurée, pas supposée.*

---

## 1. Ce qu'est DFM en une page

DFM (Dental Formation Manager) gère la formation continue dentaire pour des organismes
certifiés **Qualiopi**. Il couvre la chaîne entière : inscription d'un praticien →
convention → signature en ligne → confirmation → facture → émargement → attestation →
questionnaires → registres d'audit.

- **~90 modules Python**, Flask + Jinja2, JavaScript navigateur sans étape de compilation.
- Servi sur `127.0.0.1:5001`. Lancement : `./DFM.command` (choisit le venv, sinon
  `/usr/bin/python3`, et libère le port si un DFM oublié tourne encore).
- **Multi-organismes** : plusieurs entités juridiques cohabitent, chacune avec son
  identité, ses registres et sa numérotation de factures.

### Les trois invariants à ne jamais casser

1. **Le cloisonnement par organisme.** Deux entités = deux certifications Qualiopi.
   Un document produit pour l'organisme A doit porter l'identité de A — SIRET, IBAN,
   adresse — même si l'organisme B est actif à l'écran. La porte unique est
   `sessions.session(code)`, qui applique `_appliquer_proprietaire()`. **L'absence
   d'une valeur chez le propriétaire est une valeur** : un champ vide reste vide, il
   n'est jamais comblé par celui du voisin (défaut corrigé le 18/08/2026 — un organisme
   neuf héritait de l'IBAN de l'actif).
   *Exception assumée : les dossiers formateurs (CV, diplôme, photo) sont partagés
   entre organismes depuis le 19/08/2026 — un CV ne change pas selon l'employeur.
   Le rattachement aux formations, lui, reste par organisme.*

2. **Le journal scellé.** `journal` dans `dfm.db` est une piste d'audit chaînée :
   `HMAC(clé, rang ∥ valeurs ∥ scellé précédent)`. Les rangs sont contigus et ne se
   réattribuent pas. `journal.verifier(organisme)` recalcule la chaîne.
   **Ne jamais réécrire ni réordonner une entrée existante.**

3. **On ne détruit pas.** Retirer un document le déplace dans `documents/_corbeille`.
   Détacher un formateur ne l'efface pas. Un numéro de facture ne se réattribue jamais.

---

## 2. Ce qui tourne en local — c'est-à-dire presque tout

**Mesuré le 19/08/2026, les quatre fichiers de secrets retirés du dossier :
47 pages sur 50 répondent.** Les 3 restantes affichent un message explicite, pas une erreur.

| Domaine | Où | Autorité |
|---|---|---|
| Données de suivi, journal, état des sessions | `dfm.db` (SQLite) | **oui** |
| Formations, sessions, clients, factures, formateurs, réclamations | fichiers `.json` à la racine | **oui** |
| Documents produits (conventions, factures, attestations, émargements) | `documents/<organisme>/<session>/<catégorie>/` | **oui** |
| Pièces déposées (programme, plan d'accès, RIB, règlement) | `documents/_pieces/`, `documents/_formations/` | **oui** |
| Dossiers formateurs (CV, diplôme, photo) | `documents/_formateurs/<identifiant>/` | **oui** |
| Images d'identité (logo, signature, tampon) | `identite/<organisme>/` | **oui** |
| Justificatifs de veille | `justificatifs/<organisme>/<axe>/` | **oui** |
| Gabarits des documents | `templates/*.html` → PDF par **Chrome headless** | **oui** |

### Prérequis réels

- **Python 3.13** (testé). Flask, Jinja2, `pymupdf`, `pypdf`, `cryptography`, `supabase`.
- **Chrome ou Chromium installé** — moteur PDF, utilisé sans interface. `pdf.py` cherche
  Chrome, Chromium, `google-chrome` dans cet ordre.
  *Piège connu : Chrome headless impose un viewport minimum de 500 px. Toute mesure de
  débordement en dessous est un faux positif.*
- **macOS pour les vignettes** : `documents.vignette()` appelle `qlmanage` (Quick Look).
  Absent ailleurs → rend `None`, et l'écran retombe sur l'icône du format. Aucun blocage.
  *Piège : `qlmanage` ne rend jamais la main sur un fichier sans extension — DFM lui en
  pose une avant l'appel.*

---

## 3. Les quatre branchements — tous facultatifs

Aucun n'est requis pour démarrer. Ce sont des **branchements**, pas des dépendances.

| Fichier | Ce qu'il apporte | Absent → |
|---|---|---|
| `smtp.json` | envoi des mails | pas d'envoi ; le reste tourne |
| `config.py` | `SUPABASE_URL`, `SUPABASE_KEY` | pages publiques hors service, message explicite à l'écran |
| `credentials.json` + `token.json` | miroirs Google (Sheets, Drive) | rien — purement archivistique |

### `smtp.json`

Un mot de passe par organisme, fichier en mode `600`, **exclu des sauvegardes**.
`courrier.py` : `envoyer(message, organisme)` → SMTP si réglé, sinon repli API.
`courrier.chercher_serveur(adresse)` devine le serveur par MX (`dig`) puis par convention,
chaque candidat étant vérifié par une vraie connexion SMTP. 17 fournisseurs connus.

*Piège corrigé le 18/08/2026 : utiliser `reseau.contexte()` et non
`ssl.create_default_context()` — le Python de python.org embarque 0 autorité de
certification, d'où `CERTIFICATE_VERIFY_FAILED`.*

### Google — entièrement optionnel

Aucun script du pipeline ne meurt de Google. Vérifié en retirant `token.json` :
les 18 étapes passent, code 0. Les miroirs se rattrapent d'eux-mêmes au passage suivant.

*Deux pièges si vous rebranchez Google : l'application OAuth en mode « Test » voit son
autorisation expirer tous les **sept jours** ; et un mauvais compte connecté renvoie
**404** (« introuvable ») là où il faudrait lire « pas à vous ».*

---

## 4. Le point d'intégration — et c'est le seul

**Les pages publiques doivent être atteignables par les praticiens.** C'est la seule
raison pour laquelle quelque chose vit hors de la machine. Aujourd'hui :
**Netlify** (pages statiques + fonctions) et **Supabase** (PostgreSQL + REST).

```
  praticien ──► page Netlify ──► fonction Netlify ──► table Supabase
                                                          │
                                          DFM lit et marque « traité »
```

DFM ne parle à Supabase que par **REST**, avec `urllib` — voir `contacts.py::_appel()`.
Pas de SDK côté serveur, pas de websocket. **Le remplacement est donc mécanique :
changez l'URL et les en-têtes, gardez les tables.**

### Les six pages et leur fonction

| Page | Fonction Netlify | Table écrite |
|---|---|---|
| `inscription.html` | `inscrire.js` | `Inscriptions` |
| `index.html` (signature de convention) | `signer.js` | `Signatures` |
| `questionnaire.html` | `questionnaire.js` | `Questionnaires` |
| `reclamation.html` | `reclamer.js` | `Reclamations` |
| `annulation.html` | `annuler.js` | `Annulations` |
| `desinscription.html` | `desinscrire.js` | `Annulations` |

### Les tables — schéma réel, relevé en base

**`Inscriptions`** — ce que dépose le formulaire public.
Clé d'unicité : `(code_session, mail)`, en **upsert** : un renvoi corrigé remplace,
il ne double pas.

```
organisme, code_session,
nom (majuscules), prenom, mail (minuscules), telephone, ville, fonction, demande,
connu_par, dejeuner, restrictions, image, pmr,
importee_le          -- écrit par DFM quand la demande est reprise
```
Obligatoires côté fonction : `nom, prenom, mail, telephone, ville, fonction, demande`.
Longueurs plafonnées champ par champ (`CHAMPS` dans `inscrire.js`).

**`Sessions_inscription`** — ce que DFM publie pour alimenter le formulaire.
```
organisme, code_session, formation, titre, descriptif, date_debut, date_texte,
lieu, tarif, places_max, occupees, ouverte, couleur, maj
```

**`Organismes_publics`** — l'identité de l'organisme sur la page publique.
```
organisme, marque, accroche, logo, mail_contact, telephone_contact, maj
```

**`Signatures`** — `session, formation, praticien, signature_images, statut, created_at`
**`Questionnaires`** — `session, session_code, formation, nom, mail, type, reponses, par_objectif, score, created_at`
**`Reclamations`** — `organisme, session, qui, mail, objet, description, origine, created_at`
**`Annulations`**, **`Sessions_publiques`**, **`Contacts`** — voir `contacts.py`, `reclamations.py`, `questionnaires`.

### Ce qu'il faut fournir pour remplacer Netlify + Supabase

1. **Six pages accessibles publiquement**, paramétrées par l'URL
   (`?of=<organisme>&s=<code_session>`), qui écrivent dans vos tables.
2. **Une API REST** exposant ces tables en lecture/écriture, ou une réécriture de
   `contacts.py::_appel()` et de ses jumeaux (`inscription.py`, `reclamations.py`).
3. **`url_signature`** sur la fiche de chaque organisme doit pointer vers la racine de
   vos pages.

**Le cloisonnement se vérifie côté serveur**, pas seulement côté page : `inscrire.js`
contrôle que la session appartient bien à l'organisme annoncé. À reproduire.

---

## 5. Le traitement quotidien

`dfm.py` enchaîne **18 étapes par session**. Il tourne à 8h30 via un LaunchAgent
(`~/Library/LaunchAgents/com.dfm.pipeline-quotidien.plist`).

**`dfm.py` EXÉCUTE le pipeline à l'import.** Ne jamais faire `import dfm` pour lire
sa configuration — lisez le fichier comme du texte. *(Erreur commise deux fois le
18/08/2026 : deux exécutions non voulues, avec écritures réelles.)*

Chaque étape porte un drapeau **bloquant / non bloquant**. Une étape non bloquante qui
échoue n'arrête pas les suivantes. *Défaut corrigé le 18/08 : l'import des inscriptions
était bloquant et emportait les 17 étapes suivantes de chaque session sur une simple
erreur 503.*

*Le verrou du LaunchAgent utilise `mkdir` et non `flock` — `flock` n'existe pas sur macOS,
et le garde-fou échouait silencieusement à chaque passage.*

---

## 6. Où sont les portes

Ne contournez pas ces modules : ils portent les invariants.

| Module | Rôle |
|---|---|
| `sessions.py` | fiche d'une session, cloisonnement, héritage d'identité |
| `base.py` | SQLite — connexions par thread, WAL, schéma idempotent |
| `journal.py` + `scellement.py` | piste d'audit chaînée |
| `documents.py` | **toute** écriture et lecture de document, cache des pièces, vignettes, corbeille |
| `courrier.py` | **tout** envoi de mail |
| `profil.py` | identité d'un organisme. `_lecteur(donnees, repli=False)` pour lire un **autre** organisme — sans quoi les trous sont comblés par l'actif |
| `formateurs.py` | registre partagé, rattachement par organisme |
| `factures.py` | numérotation. Trois sources, jamais de réattribution. Clé du registre non destructrice entre organismes |
| `bibliotheque.py` | inventaire de tout ce que DFM détient |

---

## 7. Ce qui reste ouvert

- **`remise_a_zero.py`** est à jour (19/08/2026) mais **ne doit pas être exécuté** avant
  décision explicite. Simulation par défaut ; `--executer` exige trois preuves et une
  saisie manuelle.
- **Deux sessions** ont quitté Google Forms le 19/08 ; leurs anciens identifiants sont
  consignés au journal pour un retour en arrière éventuel.
- **Qualiopi** : `numero_declaration` de Smileclub = « en constitution » ; les objectifs
  B et C n'ont pas de questions ; indicateurs 22 et 25 à compléter.
- **Sauvegardes** : `.sauvegardes/` contient l'historique daté de chaque modification
  (`*.avant-<motif>`) et les archives de code retiré (`code-retire-<date>/`).
  Les copies complètes du projet sont sorties dans `~/Desktop/DFM-archives/`.

---

## 8. Vérifier qu'une reprise fonctionne

```bash
# 1. tout compile
venv/bin/python -c "import py_compile,glob; [py_compile.compile(f,doraise=True) for f in glob.glob('*.py')]"

# 2. toutes les pages répondent
./DFM.command    # puis parcourir, ou balayer url_map

# 3. les pistes d'audit sont intactes
venv/bin/python -c "import journal; print(journal.verifier('<organisme>'))"

# 4. l'inventaire des documents est cohérent
venv/bin/python -c "import bibliotheque as B; print(B.resume(B.inventaire('<organisme>')))"

# 5. le test qui compte : retirer credentials.json, token.json, smtp.json, config.py
#    → DFM doit démarrer et servir l'essentiel, avec des messages explicites
```

Ces quatre commandes sont le contrat minimal. Si elles passent, la reprise tient.
