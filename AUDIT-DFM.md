# Audit DFM — diagnostic technique

> **À lire par l'assistant qui reprend ce dossier.**
> Ce document est un rapport de diagnostic assorti d'un journal des corrections.
> Les corrections déjà appliquées sont listées dans « Journal des corrections » ci-dessous ;
> tous les autres points sont **non corrigés**.
> Ne modifie rien sans demande explicite de l'utilisateur : un point à la fois, sauvegarde
> `<fichier>.avant-<point>` avant écriture, diff montré avant application.

## Contexte

| | |
|---|---|
| Projet | DFM — gestion des formations continues d'un organisme de formation dentaire |
| Racine | `/Users/franckmoyal/Desktop/DFM` (attention : `~/DFM` est un dossier vide sans le code) |
| Pile | Python 3.9.6 / Flask (port 5001), API Google Sheets + Drive + Docs + Slides + Gmail, Supabase (signatures, annulations, questionnaires), site Netlify `site-signature/` |
| Volume | 47 fichiers Python, 8 919 lignes, dont `app.py` 4 572 lignes / 95 routes ; 21 gabarits Jinja |
| Exclu de l'audit | `.anciennes/`, `.sauvegarde-couleurs/`, `maquettes/` |
| Date de l'audit | 31 juillet 2026 |

## Résultat des vérifications mécaniques

Tout ceci a été testé et est **sain** :

- aucune erreur de syntaxe Python (`py_compile` sur les 47 fichiers)
- aucune indentation incohérente
- aucune route Flask en double
- aucune fonction définie deux fois dans un même fichier
- aucun nom utilisé avant définition (`pyflakes` : 0 undefined name)
- aucun JavaScript invalide dans les gabarits (`node --check` sur tous les blocs `<script>`, Jinja neutralisé)
- aucun gestionnaire `onclick`/`onchange` pointant vers une fonction inexistante
- `app.py` s'importe proprement, 95 routes enregistrées

**Les problèmes ne sont pas des collages ratés au sens littéral. Ce sont des branchements manquants entre les morceaux.**

---

# Journal des corrections

Une copie de sauvegarde `<fichier>.avant-<point>` est créée avant chaque modification.

| Point | Date | Fichiers | Sauvegardes | État |
|---|---|---|---|---|
| **A3** — condition d'envoi de la facture | 01/08/2026 | `envoyer_facture.py:15` | `envoyer_facture.py.avant-A3` | appliqué, à tester |
| **B3** — questionnaires envoyés malgré la synchro désactivée + journalisation des échecs | 01/08/2026 | `app.py:858-882`, `app.py:2291-2292`, `journal.py:197` | `app.py.avant-B3`, `journal.py.avant-B3` | appliqué, à tester |
| **Feuille 1** — en-têtes de session construits depuis un onglet modèle | 01/08/2026 | `app.py:179-202` (ajout `ENTETES_FORM`), `app.py:297-300` | `app.py.avant-FEUILLE1` | appliqué, à tester |
| **A5** — compteur « réponses à relever » toujours à zéro | 01/08/2026 | `app.py:2116-2118` | `app.py.avant-A5` | appliqué, à tester |
| **C1** — doublons dans `journal.PHRASES` | 01/08/2026 | `journal.py` (7 lignes retirées) | `journal.py.avant-C1` | appliqué, à tester |
| **C3** — vocabulaire de période désaligné | 01/08/2026 | `app.py:2621`, `templates/questionnaires.html:58-59` | `app.py.avant-C3`, `templates/questionnaires.html.avant-C3` | appliqué, à tester |
| **B10** — import silencieux dans les mauvaises colonnes | 01/08/2026 | `importer_inscriptions.py:4` (`import sys`), `:20-80` (contrôle d'en-têtes) | `importer_inscriptions.py.avant-B10` | appliqué, vérifié sur données réelles |
| **B8** — secrets exposés en cas de `git init` | 01/08/2026 | `.gitignore` (6 → 32 lignes) | `.gitignore.avant-B8` | appliqué, validé par dépôt git jetable |
| **C6 + C10** — profil de l'organisme non branché sur les mails et documents | 01/08/2026 | `profils/mon-organisme.json`, `sessions.py`, `app.py`, et 7 scripts d'envoi | 11 fichiers en `.avant-C6` | appliqué, vérifié par bascule à chaud |
| **C11** — modèles Google porteurs de l'identité en dur | 01/08/2026 | `sessions.py` (`balises_identite`), 3 scripts de génération, `generer_emargement.py`, `profils/mon-organisme.json`, nouveau `dupliquer_modeles.py` | `.avant-C11` | appliqué |
| **C11b** — bascule vers les modèles balisés | 01/08/2026 | `formations.json`, `parametres.json` | `.avant-C11b` | appliqué |
| **A12** — aucun moyen de régénérer la feuille d'émargement | 01/08/2026 | `suivi.py` (`lire_lignes_de`), `generer_emargement.py`, `app.py` (route), `templates/session.html` (bouton) | `.avant-C11c` | appliqué, équivalence de `lire_lignes()` démontrée |
| **B9** — plage de lecture obsolète dans `suivi.py` | 01/08/2026 | `suivi.py:41` (`A2:AN1000` → `A2:AV1000`) | `suivi.py.avant-B9` | appliqué, effet vérifié sur données réelles |
| **C2** (1/8) — journal de la feuille d'émargement | 01/08/2026 | `generer_emargement.py:99` | inclus dans `.avant-C11c` | appliqué |
| **A12b** — identifiant du document d'émargement instable | 01/08/2026 | `generer_emargement.py` (mise à jour en place au lieu de suppression + création) | `generer_emargement.py.avant-A12b` | appliqué, testé sur copie puis en réel |
| **A4** — attestations impossibles à délivrer | 01/08/2026 | `dfm.py`, `generer_attestations.py`, `envoyer_attestation.py`, `app.py` (2 routes), `templates/session.html` | `.avant-A4` | appliqué, fenêtre vérifiée sur données réelles |
| **C2** (2/8) — journal des attestations envoyées | 01/08/2026 | `envoyer_attestation.py` | inclus dans `.avant-A4` | appliqué |
| **C13 / 3a** — identifiants de question réattribués à chaque enregistrement | 01/08/2026 | `app.py` (`_ed_garder_id`), `templates/editeur.html` | `.avant-3a` | appliqué, aller-retour éditeur vérifié |
| **C14** — période par défaut masquant les sessions à venir | 01/08/2026 | `parametres.py`, `templates/conventions.html`, `templates/reglements.html` | `.avant-PERIODE` | appliqué, testé en direct |
| **3b** — instantané local des modèles à la préparation | 01/08/2026 | `questionnaires.py` (`figer`, `fige`), `app.py`, `.gitignore` | `.avant-3b` | appliqué, testé sur session jetable |
| **C15** — propositions du champ « adaptation » écrasées | 01/08/2026 | `templates/editeur.html` | inclus dans `.avant-3b` | appliqué |
| **3c** — correction contre l'instantané de session | 01/08/2026 | `questionnaires.py` (`modele_session`, `corriger_avec`), `app.py` (7 points d'appel), `templates/session.html` | `.avant-3c` | appliqué, résistance vérifiée par falsification |
| **C5** (partiel) — modèle de satisfaction figé au relevé | 01/08/2026 | `app.py:1901` | inclus dans `.avant-3c` | appliqué ; restent `_qd_axes` et `_ap_dossier` |
| **Étape 1** — bibliothèque de modèles en liste | 01/08/2026 | `app.py` (`_tp_lignes`, `page_templates`, gardes), `templates/templates.html` (réécrit), `templates/base.html` | `.avant-ETAPE1` | appliqué, vérifié dans le navigateur |
| **A2** — clôture générant l'émargement d'une autre session | 01/08/2026 | `app.py:499` (code de session + `timeout`) | `.avant-A2C9` | appliqué |
| **C9** (2/3) — journal des factures et attestations générées | 01/08/2026 | `envoyer_facture.py`, `generer_attestations.py` | `.avant-A2C9` | appliqué |
| **B1** — un échec mineur arrêtait tout le pipeline | 01/08/2026 | `dfm.py` (étapes bloquantes / non bloquantes, rapport complet) | `dfm.py.avant-B1` | appliqué, 4 scénarios testés |
| **B2** — appels à `dfm.py` sans délai de garde | 01/08/2026 | `app.py` (`_auto_executer`, `/lancer`) | `app.py.avant-B2` | appliqué |
| **C16** — rattachements de modèles effacés à la réouverture de la fiche formation | 01/08/2026 | `templates/formation_creer.html` (`qfSynchroniser`, `mfSynchroniser`, retours de création, brouillon) | `templates/formation_creer.html.avant-QF` | appliqué, vérifié sur la fiche Masterclass réelle |
| **A1** — le moteur ne connaissait que la session active | 01/08/2026 | `suivi.py` (écritures par code), 11 scripts du pipeline, `dfm.py` (boucle sessions), `envoyer_attestation.py` | `.avant-A1a` à `.avant-A1e` | appliqué en 4 paliers, **diff Usures avant/après : 0 cellule modifiée** |
| **B7** (verrou principal) — rapprochement Supabase par nom seul | 01/08/2026 | `relever_signatures.py`, `relever_annulations.py`, `generer_convention_signee.py` (`.eq("formation", …)`) | inclus `.avant-A1b/d` | appliqué |
| **C17** — URL Drive stockées telles quelles par le formulaire de formation | 01/08/2026 | `app.py` (`_extraire_id` sur 5 champs), fiche `masterclass` réparée | `app.py.avant-A1c` | appliqué |
| **C18** — pièces jointes du rappel J-20 perdues à l'enregistrement (le gabarit envoie 5 champs, la route n'en lisait qu'un) | 02/08/2026 | `app.py` : `request.form.getlist("pieces_rappel")` aux deux emplacements ; 3 pièces d'Usures restaurées depuis le littéral d'origine | `app.py.avant-C18`, `formations.json.avant-RESTAURATION` | appliqué — aller-retour 3/3 vérifié |
| **C17b** — garde-fou Drive généralisé (lien ou identifiant partout, aperçu, refus explicite) + **A6 (moitié)** : route `/verifier-document` | 02/08/2026 | `sessions.py` (`extraire_id` partagé), `parametres.py` + `profil.py` (type `drive`, `sauver` → refus), `app.py` (route de vérification, refus formation/session), 4 gabarits | `.avant-DRIVE` | appliqué, vérifié en HTTP réel et navigateur |
| **B11** — réveil à froid Supabase : seconde tentative (2 max), signalée dans le rapport | 02/08/2026 | `relever_annulations.py`, `relever_signatures.py`, `generer_convention_signee.py` | `.avant-REPRISE` | appliqué, motif testé (reprise + panne durable) |
| **Ouvrir les documents** — lien « Ouvrir » à côté de chaque champ Drive exploitable, distinct de la vérification | 02/08/2026 | `formation_creer.html` (liens réparés pour identifiants nus + affichage en édition), `parametres.html`, `profil.html`, `session_creer.html` | `.avant-REPRISE` | appliqué, vérifié navigateur |
| **A6** — `/questionnaires/relever-tout` appelée par `base.html` mais inexistante (404 avalé par un `.catch()` vide) : la relève automatique n'a jamais fonctionné | 02/08/2026 | `app.py` (route, appel de la route par session, bridage sur `releve_heures`) | `app.py.avant-A6` | appliqué — 2 sessions interrogées, bridage vérifié |
| **A7** — `/templates/balises` rendait un gabarit absent (500) ; route orpheline, aucun lien n'y menait | 02/08/2026 | `templates/balises.html` créé, lien ajouté depuis l'écran Modèles | `templates.html.avant-A7` | appliqué — 25/25 balises rendues, vérifié au navigateur |
| **C4 (partiel, 4/10)** — réglages modifiables que personne ne lisait | 02/08/2026 | `releve_heures` (via A6), `devise` (filtre `euros`), `mode_sombre` (défaut serveur, choix local prioritaire), `envois_auto_autorises` (bride la synchro automatique) | `app.py.avant-C4`, `base.html.avant-C4` | appliqué et testé |
| **C5 (solde)** — `_qd_axes` et `_ap_dossier` analysaient les réponses avec la trame de référence au lieu du modèle figé de la session | 02/08/2026 | `app.py` : `_qd_axes(liste, code_session=None)`, écran de détail d'une session, dossier apprenant (modèle par réponse) | `app.py.avant-C5` | appliqué — 8 références en dur ramenées à 1 repli |
| **Bibliothèque, étape 2** — aperçu, duplication, date de modification | 02/08/2026 | `modeles.py` + `mails.py` (`modifie_le`), `app.py` (5 routes : aperçu mail, aperçu questionnaire, duplication mail, duplication questionnaire, `/logo-organisme`), `templates.html` (modale, boutons, date) | `.avant-ETAPE2` | appliqué, vérifié au navigateur |
| **Durées de conservation** — libellés reformulés : durées déclarées, aucune purge | 02/08/2026 | `parametres.py` (3 réglages + intitulé de section) | `parametres.py.avant-CONSERVATION` | appliqué |
| **C12** — attestations en doublon dans Drive | 02/08/2026 | `generer_attestations.py` : mise à jour du contenu, identifiant stable ; exemplaires surnuméraires **signalés, jamais supprimés** | `.avant-C12` | appliqué ; dossier `Attestations` vérifié vide, aucun doublon à arbitrer |
| **C19** — modèle de document partagé entre deux formations | 02/08/2026 | `app.py` (`_c19_modeles_partages`, `_c19_nom_incoherent`), `formation_creer.html` | `.avant-C19` | appliqué — 7/7 cas de test, avertissement jamais bloquant |
| **B4** — l'aperçu du profil écrivait dans le fichier réel de l'organisme | 02/08/2026 | `profil.py` (`_lecteur` + 4 fonctions paramétrées), `app.py` | `.avant-B4` | appliqué — équivalence prouvée, fichier inchangé (empreinte) |
| **B5** — `SystemExit` levé au milieu de vues Flask | 02/08/2026 | `sessions.py` (`Inconnue(ValueError)`), `app.py` (gestionnaire), `templates/erreur.html` créé | `.avant-B5` | appliqué — 404 lisible, serveur préservé |
| **B6** — un tarif non numérique cassait le tableau de bord | 02/08/2026 | `sessions.py` (`nombre()`), `donnees.py`, `app.py` (normalisation + refus) | `.avant-B6` | appliqué — 9/9 cas |
| **B7 (solde)** — rapprochement par nom exact | 02/08/2026 | `sessions.py` (`cle_nom()`), les 3 scripts de rapprochement ; signatures orphelines désormais **signalées** | `.avant-B7` | appliqué — 6/6 cas |
| **C2 (solde)** — 7 événements rattachés à la mauvaise session | 02/08/2026 | `app.py` | `.avant-C2` | appliqué — contrôlé par analyse syntaxique (position réelle de l'argument) |
| **C7 (partiel)** — identifiant `s09` écrit en dur | 02/08/2026 | `app.py` : identifiant lu depuis le modèle de chaque session | `.avant-C7code` | appliqué |
| **Propositions d'adaptation** — interface d'édition | 02/08/2026 | `templates/editeur.html` : formulation modifiable, sens positionnel fixe et affiché | `.avant-ADAPT` | appliqué, vérifié au navigateur |
| **C7** — code mort supprimé : 8 scripts + 4 résidus de gabarits | 02/08/2026 | validé fichier par fichier ; copies conservées en `.avant-C7` ; 3 messages qui renvoyaient vers les scripts supprimés réécrits vers l'interface | `.avant-C7`, `.avant-C7msg` | appliqué |
| **C8 (A+C)** — 4 mails migrés vers l'éditeur, 6 mails figés rendus visibles | 02/08/2026 | `mails.py` (4 usages, blocs, objets), les 4 scripts, `app.py` (champs de rattachement + `_TP_MAILS_FIGES`), `templates.html` | `.avant-C8` | appliqué — **rendu identique prouvé, 4/4** |
| **C10 (solde)** — dernières coordonnées bancaires et identité en dur | 02/08/2026 | `envoyer_rappel.py` (IBAN/BIC du bloc de virement), `app.py` (repli des relances → chaîne vide), `creer_template_facture.py` (gabarit balisé), `profil.py` (exemples génériques) | `.avant-IBAN` | appliqué — rendu du rappel J-20 vérifié identique (3418 o) |
| **Migration Python (essai à blanc)** — 3.9.6 → 3.13.14 en environnement isolé | 02/08/2026 | ajouts seuls : `venv/`, `DFM.command`, `requirements.txt`, `FICHE-RETOUR-ARRIERE.md` ; aucun module modifié | `token.json.avant-MIGRATION`, `.gitignore.avant-VENV` | **essai concluant, bascule non faite — décision de l'utilisateur** |
| **Mode sombre** — 43 sélecteurs à fond clair sans couleur de texte | 02/08/2026 | `base.html` : bloc unique, 18 couleurs → 9 équivalents sombres, tous > 12:1 | `base.html.avant-SOMBRE` | appliqué — ligne sélectionnée passée de 1,11:1 à 12,42:1, mesuré au navigateur |
| **Annulation groupée** — action « Annuler l'inscription » dans la barre de sélection | 02/08/2026 | `app.py` : route `/annulation/impact-groupe` + paramètre `origine` (demande \| decision) sur la route existante ; `session.html` : bouton, écran d'impact, tableau Annulations scindé en deux | `app.py.avant-ANNUL`, `session.html.avant-ANNUL` | appliqué — écran d'impact vérifié sur données réelles, aucune écriture |
| **B7 (rectification)** — faux positif du contrôle de signatures orphelines | 02/08/2026 | `relever_signatures.py` : comparaison sur **tous** les inscrits, plus seulement ceux en attente de signature | `.avant-B7bis` | appliqué — défaut introduit avec le contrôle lui-même, repéré en le voyant se déclencher en conditions réelles sur Moshe DAYAN |
| **Motif d'annulation** — fenêtre de choix pour les annulations décidées | 02/08/2026 | `app.py` (paramètre `motif`, écrit dans la colonne AH existante), `session.html` (3 raisons + précision libre) | `.avant-MOTIF` | appliqué, vérifié au navigateur |
| **Journal (série)** — 3 défauts + piste d'audit + diff + résultat des synchros | 02/08/2026 | `envoyer_mail_attente.py` (événement jamais journalisé), `journal.py` (2 libellés doublons alignés, **27 styles manquants** — 22 % des entrées étaient inclassables donc infiltrables), `app.py` (présence rebranchée sur la validation des attestations, `_diff_fiche`, `_resume_synchro`), 6 scripts (détail d'audit : destinataire ou lien du document) | `.avant-JOURNAL`, `.avant-PRESENCE`, `.avant-AUDIT`, `.avant-DIFF`, `.avant-SYNCHRO` | appliqué |
| **Journal — colonne I `details`** | 02/08/2026 | Sheet : grille 8 → 9 colonnes, en-tête `I1` ; `journal.py` (`A:H` → `A:I`, `A2:H5000` → `A2:I5000`, paramètre `details`) ; `journal.html` (chevron + bloc dépliant) | `journal.py.avant-COLI`, `journal.html.avant-COLI` | appliqué — aller-retour vérifié, 165 entrées anciennes affichées sans chevron |
| **Apprenant invité** — chaîne complète sans volet financier | 02/08/2026 | Sheet : `AW1` = `invite_le` sur les 2 onglets ; `suivi.py` (colonne 48, plage `AW`, statut « Invitee ») ; `donnees.py` (invités hors CA, restant dû, alertes) ; `app.py` (7 plages, 2 routes, `_mail_invitation`, écran Règlements) ; `mails.py` (usage `invitation`) ; `journal.py` (2 libellés) ; `session.html`, `reglements.html` | `.avant-INVITE` | appliqué — aller-retour vérifié, retour à l'état initial exact |
| **Correction d'un règlement** — action « Retirer ce règlement » | 02/08/2026 | `app.py` (route `/reglement/corriger` : 4 colonnes vidées ensemble, statut recalculé, journal + détail long), `journal.py`, `session.html` | `.avant-CORRREG` | appliqué — aller-retour vérifié, référence restaurée à l'identique |
| **Numérotation des factures** — recherche resserrée | 02/08/2026 | `generer_factures.py` : filtre PDF + motif ancré `^Facture F<annee>-NNN` ; les fichiers écartés sont signalés | `.avant-NUM` | appliqué |
| **Remise à zéro** — inventaire **et** exécution | 02/08/2026 | `remise_a_zero.py` : simulation par défaut ; l'exécution exige **trois preuves vérifiées** (copie du dossier complète et à jour, export `.xlsx` réel et non vide, relecture des modèles) puis la recopie d'une phrase. Les 3 questionnaires de l'utilisateur sont conservés **par défaut**, en dur. | `.avant-EXEC` | écrit et testé sur 6 scénarios de refus — **jamais exécuté** |
| **Suppression de session** — écran d'impact | 02/08/2026 | `app.py` : route `/suppression/impact` — trois catégories : nettoyé d'office (sans valeur probante), proposé (conservé par défaut), jamais touché (**factures et journal**) | `.avant-SUPPR` | appliqué — vérifié en lecture seule sur la Masterclass |
| **Aperçu des modèles dans l'assistant** — 5 sélecteurs | 02/08/2026 | `formation_creer.html` : bouton œil à côté de chaque sélecteur (2 mails, 3 questionnaires), fenêtre d'aperçu. **Aucune route nouvelle** — réutilisation de `/templates/mail/<usage>/<id>/apercu` et `/templates/questionnaire/<type>/<id>/apercu`, qui gèrent déjà le cas « fourni avec DFM » | `.avant-APERCU` | appliqué — vérifié au navigateur, aucune saisie perdue |
| **Brouillons** — 5 écrans de saisie longue | 02/08/2026 | `base.html` : module commun `dfmBrouillon` (localStorage, deux signaux concordants, bandeau de reprise, dialogue à 3 boutons) ; branché sur `editeur.html`, `formation_creer.html`, `session_creer.html`, `editeur_mail.html`, `parametres.html`, `profil.html`. **Correction au passage** : `emMarquerModifie` comparait le titre à la chaîne vide — toujours vrai sur un modèle existant. | `.avant-BROUILLON` | appliqué — consultation pure vérifiée sans faux positif, cycle complet testé au navigateur |
| **Page de signature** — valeurs de session écrites en dur | 02/08/2026 | `site-signature/index.html` (dates, lieu, montant lus du lien ; repli neutre pour les anciens liens), `envoyer_mail_signature.py` | `.avant-SESSION` | appliqué et **publié** — tout inscrit hors Usures lisait les dates d'Usures sur la page où il signe son contrat |
| **Densité des écrans Paramètres et Profils** | 02/08/2026 | `parametres.html` : aide sur la même ligne que l'intitulé (jamais en infobulle), en-têtes compactés — **3,1 → 2,4 écrans** ; `profil.html` : grille deux colonnes ≥ 900 px, espacements resserrés — **4,3 → 3,0 écrans** | `.avant-DENSITE` | appliqué — contrastes sombres vérifiés, contrôles ≥ 36 px |
| **Journal — flèche menant à une session sans rapport** | 02/08/2026 | `journal.py` : suppression du repli `code_session or S["code"]` qui estampillait **49 entrées globales sur 182** avec la session active ; `SANS_SESSION` + `session_ouvrable()` corrigent l'affichage des entrées déjà écrites sans toucher au Sheet ; `app.py` et `cloturer_inscriptions.py` : 2 appels session-dépendants qui comptaient sur ce repli reçoivent leur code | `.avant-FLECHE` | appliqué — 133 flèches actives, 49 remplacées par une cale ; clic vérifié au navigateur |
| **Recherche de doublons** — balayage de toute la base apprenants | 02/08/2026 | `doublons.py` créé (normalisation, 2 critères, écartements persistants), `app.py` (3 routes + `_ap_toutes_lignes`), `templates/doublons.html`, bouton sur `/inscrits`, `journal.py` (libellé « Rapprochement écarté »), `.gitignore` | `.avant-DOUBLONS` | appliqué — 2 familles distinctes, fusion existante réutilisée, aucune fusion automatique |
| **Convention consultable avant signature** | 02/08/2026 | `generer_convention_apercu.py` créé (étape 4 du pipeline, **non bloquante**), `dfm.py` (12 étapes), `envoyer_mail_signature.py` (lien du PDF), `index.html` (bouton) | `.avant-APERCUCONV`, `.avant-BOUTON` | appliqué et publié — PDF vérifié lisible sans compte Google |
| **Site de signature — hygiène** | 02/08/2026 | 4 résidus sortis du dossier publié (dont `questionnaire.bak`, 15 Ko) ; `netlify.toml` en chemins relatifs | `netlify.toml.avant-RELATIF`, `site-signature-residus/` | appliqué — résidus en 404 sur le site |

### C16 — détail (signalé par l'utilisateur le 01/08/2026)

Symptôme rapporté : un modèle d'évaluation sélectionné à l'étape 3 de l'assistant ne « tenait pas » à la réouverture de la fiche en modification. Diagnostic : la valeur était **bien enregistrée** dans `formations.json` ; c'est la réouverture qui la détruisait en mémoire. Les listes déroulantes sont chargées en asynchrone, et une fois remplies, `qfChoisir`/`mfChoisir` copiaient le select — **fraîchement reconstruit, donc vide** — vers les champs cachés. Conséquence réelle : bien pire qu'un défaut d'affichage — un simple ré-enregistrement depuis cette fiche envoyait `modele_*=""` et **détachait silencieusement les cinq modèles** (évaluation, satisfaction, à froid, deux mails).

Correctif : fonctions `qfSynchroniser`/`mfSynchroniser` qui vont dans le sens fiche → select (priorités : brouillon restauré > `FICHE_EDIT` > champ caché). Un modèle enregistré mais absent de la bibliothèque n'est **pas effacé** : la fiche affiche « Modèle enregistré introuvable dans la bibliothèque ».

Dans la foulée, deux défauts de la même famille (perte de travail silencieuse) :
- `qfCreer`/`mfCreer` renvoyaient en dur vers `/formations/nouvelle` après création d'un modèle, **même depuis une fiche en modification** — l'édition en cours était perdue. Corrigé : retour vers `location.pathname`.
- Le brouillon (`sessionStorage`) s'appliquait à n'importe quelle page du formulaire et était ensuite écrasé par `remplirEdition`. Corrigé : le brouillon porte sa page d'origine (`__origine`) et ne s'applique qu'à elle ; restauré, il prime sur le pré-remplissage (`__brouillonRestaure`).

### A1 — réalisé le 01/08/2026, déclenché par la seconde session réelle

La session `masterclass-oct26` a fourni le cas réel : inscription de Moshe DAYAN invisible, chaîne muette — le pipeline ne regardait qu'`usures-nov26`. Quatre paliers, chacun testé en réel :

1. **Écritures par session** dans `suivi.py` (`ecrire`/`marquer`/`rafraichir_statuts` + `code=None`), équivalence prouvée par interception. Correction immédiate d'un croisement latent introduit par A4 : `envoyer_attestation.py` lisait le bon onglet mais écrivait dans celui de la session active.
2. **Les 11 scripts du pipeline** acceptent le code en argument (sans argument : session active, comportement historique). Verrou Supabase par formation au passage (B7). Découverte et correction de **C17** : la fiche formation stockait des URL Drive complètes au lieu d'identifiants — toute la chaîne documentaire de la Masterclass aurait échoué.
3. **`dfm.py` boucle sur les sessions** (ordre chronologique, archivées sautées), étapes en interne : un échec bloquant n'abandonne que SA session. Chaque étape du rapport porte `session`.
4. **Preuves** : synchronisation complète réelle — 2 sessions, 22/22 étapes ; **diff cellule par cellule de l'onglet Usures : zéro modification** ; Moshe importé, mail de signature reçu, statut « En attente signature », journal rattaché à `masterclass-oct26` ; audit final : plus aucune écriture `suivi.ecrire`/`marquer` sans code dans le pipeline.

Restent hors périmètre, volontairement : les scripts CLI orphelins (`saisir_reglement.py`, `valider_annulation.py`, `relancer.py`, `pointer_presences.py`, `promouvoir_attente.py`, `cloturer_inscriptions.py` — point C7) qui travaillent toujours sur la session active ; `SESSION_ACTIVE` subsiste comme repli sans argument, désormais inoffensif puisque le pipeline passe toujours le code.

### Incident du 01/08/2026 — régression de `app.py`

À 17:25:43, `app.py` a été restauré sur le disque dans un état **octet pour octet identique à `app.py.avant-3c`**, effaçant d'un coup les corrections **3c** et **Étape 1**. Les autres fichiers n'ont pas bougé, d'où un symptôme trompeur : le nouveau gabarit `templates.html` s'affichait, mais la route lui envoyait les anciennes variables — bandeau sans chiffres, liste vide.

Cause probable : un tampon d'éditeur antérieur enregistré par-dessus. Les deux corrections ont été réappliquées et vérifiées.

**Protocole renforcé à la demande de l'utilisateur** : après chaque écriture, relire le fichier **depuis le disque** et vérifier la présence effective des modifications. La compilation ne prouve que l'absence d'erreur de syntaxe, pas que le contenu est le bon. Un témoin horodaté (`app.py.reprise-173522`) permet de détecter immédiatement une nouvelle régression.

**Ordre convenu pour la suite** : B8 (secrets) → C6 (Profils OF non branchés sur les mails et documents) → C5 (questionnaires de satisfaction personnalisés jamais dépouillés) → A4 (pointage des présences) → A6 (routes manquantes).

~~**A1 est reporté**, sur décision de l'utilisateur du 01/08/2026 : une seule session existe, elle fonctionne, et le chantier est trop risqué sans nécessité. À traiter au moment de créer la deuxième session, sur une copie du Sheet avec des adresses de test.~~

> **PÉRIMÉ — ne pas s'y fier.** Ce paragraphe décrit une décision du matin du 01/08/2026. A1 a été **réalisé le jour même**, en quatre paliers, déclenché par la création de la seconde session. Voir « A1 — réalisé le 01/08/2026 » plus haut, et la ligne A1 du tableau de suivi. Le moteur traite aujourd'hui plusieurs sessions : `dfm.py` boucle dessus, `suivi.ecrire()` écrit dans l'onglet du code qu'on lui passe. *Mention laissée barrée plutôt que supprimée : elle documente une décision réelle, mais elle a induit en erreur le 03/08/2026 et ne doit plus jamais être lue comme l'état courant.*

Restent ouverts et non planifiés : A2, A7, B1, B2, B4, B5, B6, B7, B9, C2, C4, C7, C8, C9.

### Correction apportée au rapport lui-même

Le point sur l'onglet `Feuille 1`, soulevé le 01/08/2026, reposait sur une hypothèse fausse : je le présentais comme un onglet résiduel dont le contenu risquait d'être arbitraire. Vérification faite, `Feuille 1` est l'onglet de réponses du Google Form, ses 13 intitulés correspondent exactement aux indices 0-12 de `suivi.COL`, et le mécanisme d'`app.py:276-286` était intentionnel et correct. L'onglet `Usures-nov26` présentait **0 écart sur 48 colonnes** avec ce que le code produisait, et a bien été créé par l'application (`columnCount=52`, signature de `app.py:270`). **Aucun dégât.** La correction appliquée ne réparait donc pas une erreur en cours mais supprimait trois fragilités réelles : une `IndexError` possible ligne 285 laissant un onglet sans en-têtes, une sélection de modèle dépendante de l'ordre des onglets, et un `48` codé en dur. C'est en creusant ce point qu'a été découvert **B10**, nettement plus grave.

---

# A. Ce qui est cassé

## A1. Le moteur de traitement ne connaît qu'une seule session, écrite en dur

> **RÉSOLU le 01/08/2026.** Ce qui suit décrit l'état AVANT correction, conservé pour mémoire.


**Où** : `sessions.py:99` → `SESSION_ACTIVE = "usures-nov26"`

27 fichiers font `S = session()` sans argument : `suivi.py:4`, `journal.py:4`, `importer_inscriptions.py:5`, `envoyer_mail_signature.py:10`, `envoyer_mail_confirmation.py:10`, `generer_factures.py:8`, `generer_attestations.py:7`, `generer_emargement.py:7`, `generer_convention_signee.py:9`, `envoyer_facture.py:9`, `envoyer_attestation.py:9`, `envoyer_rappel.py:10`, `envoyer_mail_attente.py:8`, `relever_signatures.py:5`, `relever_annulations.py:5`, `cloturer_inscriptions.py:7`, etc.

Aucun script n'accepte d'argument de session (`sys.argv` n'apparaît que dans `preparer_onglet.py` et `voir_journal.py`, pour autre chose).

**Conséquence utilisateur** : on peut créer autant de sessions que l'on veut dans l'interface — `/lancer`, `/synchro/relancer` et la synchro automatique ne traiteront jamais que `usures-nov26`. Les inscriptions des autres sessions ne sont jamais importées, leurs mails jamais envoyés, leurs conventions jamais générées. Le code en a conscience : `app.py:530` refuse la suppression avec le message « Change la session active dans sessions.py » — un fichier source, pas un réglage.

**Proposition** : faire accepter `sys.argv[1]` (code de session) à chaque script, avec repli sur `SESSION_ACTIVE`, et faire boucler `dfm.py` sur les sessions non archivées en passant le code. `suivi.py` et `journal.py` devront exposer `lire_lignes(code)` / `ecrire(..., code)` au lieu de figer `ONGLET` et `S` à l'import (`suivi.py:4-6`, `journal.py:4`).

---

## A2. Clôturer une session génère la feuille d'émargement d'une autre

**Où** : `app.py:485`

```python
r = subprocess.run([sys.executable, "generer_emargement.py"],
                   capture_output=True, text=True, cwd=DOSSIER)
```

Aucun code de session transmis ; `generer_emargement.py:7` fait `S = session()` → session active. Les lignes `app.py:491-496` écrivent ensuite le lien obtenu dans la ligne Sessions de `code`.

**Conséquence utilisateur** : on clôture la session B, DFM produit la feuille d'émargement de la session A (mauvais participants, mauvaises dates, mauvais titre) et l'enregistre comme étant celle de B. Le PDF est signé en séance par les vrais participants sur une feuille qui n'est pas la leur — pièce non conforme en cas de contrôle Qualiopi.

**Proposition** : passer `code` en argument et le lire dans `generer_emargement.py`. En attendant, ne pas utiliser le bouton de clôture pour une session autre que l'active.

---

## A3. La facture est renvoyée en boucle, puis plus jamais

**Où** : `envoyer_facture.py:15`

```python
a_envoyer = [l for l in lignes if l["facture_le"] and l["lien_facture"] and not l["attestation_le"]]
```

La garde porte sur `attestation_le`. Le script écrit pourtant `facture_envoyee_le` en `envoyer_facture.py:60` — colonne jamais relue nulle part comme condition d'envoi.

**Conséquence utilisateur, double** :
1. Tant que l'attestation n'existe pas, le praticien reçoit **la même facture à chaque passage du pipeline** (toutes les 5 minutes en synchro auto par défaut, `app.py:825`).
2. L'ordre de `dfm.py:17-20` place la génération des attestations *après* l'envoi des factures : si une attestation est produite avant que la facture ne parte, la facture **ne partira jamais**.

**Proposition** : remplacer `not l["attestation_le"]` par `not l["facture_envoyee_le"]`.

---

## A4. Les attestations ne peuvent pas être générées depuis l'application

**Où** : `generer_attestations.py:18`

```python
a_generer = [l for l in lignes if l["present"] == "oui" and not l["attestation_le"]]
```

La colonne `present` n'est écrite que par `pointer_presences.py:18` et `:38` — un script interactif (`input()` ligne 30) qui n'est lancé ni par `app.py`, ni par `dfm.py`. Aucune route Flask n'écrit `present` : l'application ne fait que le lire (`app.py:2714`, `app.py:3217`, `app.py:2740`).

**Conséquence utilisateur** : les étapes 11 et 12 du pipeline sont inertes en permanence. `generer_attestations.py:24` affiche « N participant(s) sans pointage de presence » puis sort — mais **avec un code retour 0**, donc `dfm.py` marque l'étape « OK » et le rapport de synchro annonce que tout s'est bien passé. Aucune attestation n'est jamais délivrée sans ouvrir un terminal.

**Proposition** : ajouter une route de pointage des présences (le gabarit `session.html` a déjà la liste des participants) écrivant `present` = `oui`/`non`, et faire sortir `generer_attestations.py` en code ≠ 0 quand il ne peut rien produire, pour que l'échec remonte dans le rapport.

---

## A5. Le compteur « réponses à relever » vaut toujours zéro

**Où** : `app.py:2087-2096`

```python
faits = {"init": 0, "fin": 0, "satisfaction": 0}
CH = {"init": "eval_init_le", "fin": "eval_fin_le", "satisfaction": "satisfaction_le"}
...
for quoi in _Q_TYPES:                       # _Q_TYPES contient aussi "froid"
    a_relever += max(0, len(repondants.get(quoi) or []) - faits[quoi])
except Exception:
    a_relever = 0
```

`faits["froid"]` lève `KeyError`. Le bloc est enveloppé dans un `try/except` qui remet `a_relever` à 0, **écrasant le total accumulé sur les trois premiers types**.

**Conséquence utilisateur** : sur la fiche de session, l'indicateur « réponses à relever » affiche systématiquement 0. On ne sait jamais qu'il y a des questionnaires à récupérer.

**Proposition** : ajouter `"froid": 0` à `faits` (ligne 2087) et `"froid": "froid_le"` à `CH` (ligne 2088).

---

## A6. Deux appels de gabarit pointent dans le vide

### `/questionnaires/relever-tout`

**Où** : `base.html:347`

```javascript
fetch("/questionnaires/relever-tout", {method: "POST"})
  .then(...).catch(function(){});
```

Route inexistante (vérifié : 95 routes enregistrées, celle-ci absente). L'appel part sur chaque affichage de `/`, `/questionnaires*` et `/session/*`, prend un 404, et le `catch` vide l'efface.

**Conséquence utilisateur** : la relève automatique des réponses aux questionnaires, annoncée par le paramètre « Relève des questionnaires — fréquence de récupération… elle a lieu aussi à l'ouverture des écrans concernés » (`parametres.py:34-36`), ne se produit jamais. Il faut cliquer « relever » à la main sur chaque session.

### `/verifier-document`

**Où** : `formation_creer.html:616`

Route inexistante également.

**Conséquence utilisateur** : dans le formulaire de création de formation, le contrôle des identifiants Drive (programme, plan d'accès, modèles de convention et d'attestation) affiche toujours « Erreur de vérification ». On saisit des identifiants sans jamais savoir s'ils sont valides — ce qui alimente directement le point **B1**.

**Proposition** : écrire les deux routes, ou retirer les appels. La première peut réutiliser telle quelle la logique de `relever_questionnaires` (`app.py:1813`) en bouclant sur les sessions.

---

## A7. Route vivante, gabarit absent

**Où** : `app.py:4119-4123` → `render_template("balises.html", ...)`. Le fichier `templates/balises.html` n'existe pas.

**Conséquence utilisateur** : `/templates/balises` renvoie une erreur 500. Atténuation : aucun gabarit ne pointe vers cette URL, elle n'est atteignable qu'en la tapant à la main.

**Proposition** : créer le gabarit ou supprimer la route (les données `mails.BALISES` sont déjà affichées dans `editeur_mail.html`).

---

# B. Ce qui est fragile

## B1. Une fiche formation incomplète arrête tout le pipeline

**Où** :
- `envoyer_mail_signature.py:24` → `drive.files().get_media(fileId=S["programme_id"])`
- `envoyer_mail_confirmation.py:23-24` → `S["rib_id"]`, `S["acces_id"]`
- `generer_factures.py:9` → `S["template_facture"]`
- `generer_attestations.py:8` → `S["template_attestation"]`

Ces champs sont facultatifs dans le formulaire (`app.py:155-159` les initialisent à `""`). Un identifiant vide ou faux fait lever `HttpError`, le script sort en code ≠ 0, et `dfm.py:73` fait `sys.exit(1)` : **toutes les étapes suivantes sont abandonnées**.

**Conséquence utilisateur** : créer une formation sans PDF de programme, et le pipeline s'arrête à l'étape 4. Les signatures ne sont plus relevées, les conventions plus générées, les factures plus émises — pour *toutes* les sessions, y compris celles qui allaient bien.

**Proposition** : vérifier les identifiants requis en tête de chaque script et sortir avec un message explicite **en code 0** (« formation X sans programme, ignorée ») plutôt que de laisser remonter l'exception ; ou rendre ces cinq champs obligatoires à l'enregistrement d'une formation.

### Argument supplémentaire ajouté le 01/08/2026

La correction de **B10** introduit volontairement un second point d'arrêt à l'étape 1 : le contrôle d'en-têtes interrompt l'import, donc les onze étapes suivantes, quand le Google Form ne correspond plus aux colonnes du suivi. Ce blocage est justifié — un import corrompu s'auto-verrouille et ne se répare pas en relançant — mais il aggrave mécaniquement le défaut décrit ici : un problème circonscrit à une session empêche le traitement de tout le reste.

**Ne pas résoudre cela en affaiblissant le contrôle de B10.** La bonne réponse est de rendre `dfm.py` résilient : poursuivre les étapes suivantes après un échec non bloquant, et ne s'arrêter que sur les échecs qui compromettent la suite. Cela suppose de distinguer, dans `ETAPES` (`dfm.py:8-21`), ce qui est bloquant de ce qui ne l'est pas, et de faire remonter tous les échecs dans le rapport plutôt que le premier seulement.

---

## B2. `/lancer` peut figer une requête HTTP indéfiniment

**Où** : `app.py:4563-4566`

```python
r = subprocess.run([sys.executable, "dfm.py"], capture_output=True, text=True, cwd=DOSSIER)
```

Pas de `timeout`, contrairement à `/synchro/relancer` (`app.py:4544`, `timeout=600`) qui fait exactement la même chose. Or `connexion.py:27` appelle `flow.run_local_server(port=0)` quand le jeton n'est plus rafraîchissable : le sous-processus ouvre un navigateur et **attend**. En `capture_output=True`, l'invite n'est même pas visible.

Même mécanisme dans `_auto_executer` (`app.py:848`), qui garde en plus le verrou `_AUTO_VERROU` : la synchro automatique est alors morte pour de bon.

**Conséquence utilisateur** : le bouton reste bloqué, le thread Flask aussi, jusqu'à redémarrage manuel du serveur.

**Proposition** : ajouter `timeout=600` aux trois appels (`app.py:848`, `4544`, `4565`) et traiter `subprocess.TimeoutExpired`.

---

## B3. L'interrupteur de synchro automatique ne coupe pas les envois de questionnaires

**Où** : `app.py:858-867`

```python
def _auto_boucle():
    while True:
        _time.sleep(20)
        try:
            _q_auto()                    # <-- exécuté AVANT le test
        except Exception:
            pass
        if not _AUTO_ETAT["actif"]:
            _AUTO_ETAT["prochain"] = 0
            continue
```

`_q_auto()` (`app.py:2242`) envoie de vrais mails aux participants. Il tourne toutes les 20 secondes **même quand la synchro automatique est désactivée**.

De plus, `app.py:2276` (`except Exception: continue`) et le `except: pass` ci-dessus effacent tout échec.

**Conséquence utilisateur** : on coupe l'automatisme dans l'interface, et DFM continue à envoyer seul les questionnaires dès que l'heure planifiée est atteinte. À l'inverse, si un envoi échoue, aucune trace, aucune alerte.

**Proposition** : déplacer l'appel `_q_auto()` après le test `if not _AUTO_ETAT["actif"]`, et journaliser les échecs au lieu de les avaler (`journal.ecrire` existe déjà).

---

## B4. L'aperçu du profil écrit dans le vrai fichier de l'organisme

**Où** : `app.py:4456-4466`

```python
chemin = PR._chemin(PR.actif())
try:
    with open(chemin, "w", encoding="utf-8") as f:
        _json.dump(fusion, f, ensure_ascii=False)     # écrase la fiche réelle
    sortie = {...}
finally:
    with open(chemin, "w", encoding="utf-8") as f:
        _json.dump(ancien, f, ensure_ascii=False)     # restaure
```

**Conséquence utilisateur** : pendant la fraction de seconde de l'aperçu, toute autre requête (envoi de mail, génération de convention, contrôle `_of_garde`) lit les données de l'aperçu. Si le serveur est arrêté à cet instant, la fiche de l'organisme reste figée sur des valeurs non enregistrées.

**Proposition** : rendre `clause_parties`, `pied_legal`, `mention_tva`, `adresse_complete`, `verifier` capables de prendre un dictionnaire en paramètre — `verifier(donnees)` le fait déjà (`profil.py:330`). Aucun fichier à écrire.

---

## B5. `SystemExit` levé au milieu de vues Flask

**Où** : `sessions.py:102` et `sessions.py:125`

```python
raise SystemExit(f"Session inconnue : {code} (disponibles : {', '.join(SESSIONS)})")
```

`SystemExit` hérite de `BaseException` : le gestionnaire d'erreurs de Flask ne l'intercepte pas. Ces fonctions sont appelées par des vues, parfois en boucle sur toutes les sessions : `app.py:1468`, `2350`, `3150`, `3694`, `2177`, `2217`.

**Conséquence utilisateur** : une seule session dont la formation a été supprimée hors de l'application, et `/reglements`, `/conventions`, `/questionnaires`, `/apprenant/...` se coupent brutalement au lieu d'afficher une erreur lisible.

**Proposition** : lever `ValueError` et laisser `dfm.py` / les scripts CLI le convertir en sortie propre.

---

## B6. Un tarif non numérique casse le tableau de bord

**Où** : `donnees.py:55` → `tarif = float(S["tarif"])`, sans `try`, alors que le reste du fichier protège systématiquement ses conversions (lignes 51-54, 221-224).

Le formulaire accepte n'importe quelle chaîne (`app.py:150` : `(d.get("tarif") or "0").strip()`).

**Conséquence utilisateur** : saisir « 975 € » ou « 1 200 » à la création d'une formation, et `/`, `/formations`, `/sessions`, `/inscrits` renvoient tous une erreur 500. L'application devient inutilisable jusqu'à correction manuelle de `formations.json`.

**Proposition** : envelopper la conversion, ou valider le tarif à l'enregistrement dans `app.py:150`.

---

## B7. Le rapprochement Supabase se fait par nom, toutes sessions confondues

**Où** :
- `relever_signatures.py:16` → `supabase.table("Signatures").select("praticien, created_at").execute()`
- `relever_annulations.py:15` → idem sur `Annulations`
- `generer_convention_signee.py:42` → `.eq("praticien", nom_prenom)`

Aucun filtre de session, et la clé est la concaténation `"prenom nom"` — sensible à la casse, aux accents, aux espaces.

**Conséquence utilisateur** : un praticien inscrit à deux formations est marqué « signé » sur les deux dès qu'il signe pour l'une. À l'inverse, « Marie-Claire Dupont » saisie « Marie Claire Dupont » côté formulaire n'est jamais rapprochée et reste bloquée en « En attente signature » indéfiniment, sans qu'aucun message ne le signale (`relever_signatures.py:30` se contente d'un « pas encore signe »).

**Proposition** : ajouter la colonne `session_code` dans les tables Supabase et filtrer dessus ; à défaut, normaliser le nom des deux côtés (minuscules, accents retirés, espaces compressés).

---

## B8. Secrets en clair dans le dossier

- `config.py:2` → `SUPABASE_KEY = "sb_secret_..."` — clé **de service**, qui contourne toutes les règles RLS.
- `credentials.json` et `token.json` à la racine — jeton OAuth Google actif portant les scopes Sheets, Drive, Documents et **Gmail envoi**.
- `profils/dsf.json` et `profils/mon-organisme.json` contiennent SIRET et IBAN.

`.gitignore` couvre `config.py` mais **pas** `credentials.json`, **pas** `token.json`, **pas** `profils/`. Il liste `profil.json`, fichier qui n'existe pas : `profil.py:3` le référence encore, mais les données réelles vivent dans `profils/*.json` depuis `profil.py:101`.

État actuel : le dossier **n'est pas encore un dépôt git**, donc rien n'a été publié.

**Proposition** : avant tout `git init`, compléter `.gitignore` avec `credentials.json`, `token.json`, `profils/`, `sessions.json`, `formations.json`, `bibliotheque.json`, `questionnaires_etat.json`. Faire tourner la clé Supabase si elle a déjà circulé.

### Correction appliquée — 01/08/2026

`.gitignore` porté de 6 à 32 lignes, en quatre sections commentées : secrets, identité de l'organisme et données personnelles, sauvegardes de travail, bruit système.

**Validation** : dépôt git jetable créé dans un répertoire temporaire, arborescence réelle reconstituée (451 fichiers vides), `.gitignore` copié, puis `git check-ignore` sur chaque chemin. Les 20 fichiers sensibles ressortent ignorés ; les 9 fichiers de code témoins (`app.py`, `journal.py`, `suivi.py`, `sessions.py`, `dfm.py`, `importer_inscriptions.py`, `AUDIT-DFM.md`, `templates/session.html`, `site-signature/netlify/functions/signer.js`) restent suivis. Dépôt jetable supprimé après contrôle.

Corrections d'inventaire par rapport au diagnostic initial : `profil.json` figurait déjà dans l'ancien `.gitignore` mais **n'existe pas** — les données réelles vivent dans `profils/*.json`, qui n'était pas couvert. L'entrée est conservée car `profil.py:3` la référence encore comme repli.

Ajouts non prévus au diagnostic initial : `.anciennes/` (66 fichiers contenant l'IBAN, 3 le SIRET), `*.avant-*` (les sauvegardes de cet audit, qui embarquent l'IBAN via les copies d'`app.py`), `*.safe`, `*.AVANT_NETTOYAGE`, `site-signature/.netlify/`.

**Vérifié et sans danger** : les fonctions Netlify (`site-signature/netlify/functions/*.js`) lisent leurs clés dans `process.env`, elles ne les embarquent pas. Les archives `.zip` déployées ne contiennent aucune clé. `.anciennes/` ne contient **aucun** secret Supabase ni Google.

**Conséquence assumée** : `formations.json` et `sessions.json` étant exclus, un clone du dépôt n'aurait ni formation ni session. Choix confirmé par l'utilisateur — les sauvegardes se font par copie du dossier, pas par git.

### Rotation de la clé Supabase : PRÉALABLE BLOQUANT AVANT TOUTE MISE EN LIGNE

État constaté le 01/08/2026 : le dossier n'a jamais été un dépôt git, n'a jamais été publié, et personne d'autre que l'utilisateur n'y a accès. **La clé n'a pas circulé** — elle n'est pas compromise à ce jour, et n'est donc pas tournée.

Elle le deviendra dès la première mise en ligne, quelle qu'en soit la forme : dépôt distant même privé, déploiement sur un serveur, partage du dossier, sauvegarde dans un service tiers.

**À faire à ce moment-là, avant la mise en ligne, pas après** :

1. Générer une nouvelle clé de service dans Supabase et révoquer l'ancienne.
2. Sortir `SUPABASE_KEY` du code : la lire depuis une variable d'environnement, comme le font déjà les fonctions Netlify (`site-signature/netlify/functions/signer.js:5-6`).
3. Faire de même pour `credentials.json` et `token.json`, ou vérifier explicitement qu'ils restent hors du périmètre publié.

Rappel de ce qui est en jeu, tel qu'établi lors de l'inventaire :

| Fichier | Contenu | Portée pour qui l'obtient |
|---|---|---|
| `token.json` | jeton d'accès + **jeton de rafraîchissement** Google (103 car.), portées `spreadsheets`, `documents`, `drive`, `gmail.send` | Lire et modifier **tout** le Drive, et **envoyer des mails au nom de l'utilisateur**. Le jeton de rafraîchissement reste valide **jusqu'à révocation** : le champ `expiry` ne protège de rien, c'est le fichier lui-même qui est sensible. |
| `credentials.json` | `client_id` + `client_secret` OAuth (`GOCSPX-…`) | Se faire passer pour l'application Google et redemander des autorisations. |
| `config.py` | `SUPABASE_KEY`, préfixe `sb_secret_` — clé de **service** | Lire, modifier et **supprimer** toutes les tables Supabase en contournant les règles RLS : signatures, annulations, réponses aux questionnaires. |

---

## B9. Plage de lecture obsolète dans `suivi.py`

**Où** : `suivi.py:35` → `range=f"'{ONGLET}'!A2:AN1000"`

`AN` est la 40ᵉ colonne (indices 0-39), or `COL` va jusqu'à l'indice 47 (`suivi.py:20-21`). Les huit colonnes de questionnaires (`eval_init_le`, `score_init`, `eval_fin_le`, `score_fin`, `satisfaction_le`, `note_satisfaction`, `froid_le`, `note_froid`) sont donc toujours lues vides. `donnees.py:26` et les sept lectures dans `app.py` (lignes 673, 724, 1474, 2356, 3156, 3700) utilisent `AV`, la bonne borne — `suivi.py` est le seul resté en arrière.

**Conséquence utilisateur** : aujourd'hui, aucune donnée perdue, car aucun script autonome n'exploite ces colonnes (vérifié). C'est un piège latent : le premier script qui voudra les lire verra des cases vides sans la moindre erreur.

**Proposition** : passer la plage à `A2:AV1000`.

### Correction appliquée — 01/08/2026, et rectification du diagnostic

`suivi.py:41` : `A2:AN1000` → `A2:AV1000`. Une seule ligne, dans un passage séparé de A12 pour que la démonstration d'équivalence de `lire_lignes()` porte sur un code inchangé par ailleurs.

**Le diagnostic ci-dessus minimisait la portée.** Il annonçait un piège purement latent. La vérification après correction, en comparant l'ancienne et la nouvelle version sur les données réelles, montre que **la donnée existait déjà et était simplement hors de portée** :

| Praticien | colonne | avant (AN) | après (AV) |
|---|---|---|---|
| Bruce WAYNE | `score_init` | `''` | `'35'` |
| Bruce WAYNE | `score_fin` | `''` | `'100'` |
| Bruce WAYNE | `note_satisfaction` | `''` | `'5'` |
| Donald TRUMP | `score_init` | `''` | `'29'` |
| Donald TRUMP | `score_fin` | `''` | `'82'` |
| Donald TRUMP | `note_satisfaction` | `''` | `'4,25'` |

L'impact pratique restait nul faute de script consommateur, mais la formule « aucune donnée perdue » était trompeuse : toute lecture par `suivi.lire_lignes()` renvoyait des cases vides là où le Sheet contenait des valeurs. Vérifié également : les 40 colonnes hors questionnaires sont inchangées, et le nombre de lignes est identique.

---

## B10. L'import recopie les réponses du formulaire par position, sans jamais les vérifier

> Repéré le 01/08/2026 en investiguant l'onglet `Feuille 1`. **Corrigé le 01/08/2026** — contrôle d'en-têtes bloquant dans `importer_inscriptions.py`.
> À traiter **avant** de créer une seconde formation avec son propre Google Form.

**Où** : `importer_inscriptions.py:20-26` et `:56-62`

```python
reponses = sheets.spreadsheets().values().get(
    spreadsheetId=S["sheet_reponses"], range="A1:M1000").execute().get("values", [])
...
inscriptions = reponses[1:]          # reponses[0] = les en-tetes, lus puis jetes
...
sheets.spreadsheets().values().append(
    range=f"'{S['onglet_suivi']}'!A:M",   # recopie brute, par position
    body={"values": nouvelles})
```

La ligne d'en-têtes du formulaire est lue puis abandonnée. Elle n'est comparée ni à `ENTETES_FORM` (`app.py:179-202`), ni à la ligne 1 de l'onglet de suivi, ni à quoi que ce soit. Les lignes de réponses sont recopiées telles quelles dans les colonnes A:M, **par position**.

**Trois défaillances, toutes muettes** :

1. **Question insérée ou déplacée dans le Form** → toutes les colonnes suivantes se décalent. `suivi.COL["mail"]` vaut 3 : la colonne D contiendrait le téléphone. Les mails de signature partiraient vers une valeur qui n'est pas une adresse.
2. **Plus de 13 questions** → `range="A1:M1000"` tronque à la colonne M. Les réponses au-delà sont perdues sans message.
3. **Le dédoublonnage continue de fonctionner** (`importer_inscriptions.py:32`, clé = `l[0]`, l'horodateur, toujours en colonne A). L'import se déroule donc en apparence normalement, ce qui masque le décalage.

**Conséquence utilisateur** : en aval, `demande` (indice 7) pilote `calculer_statut`, `nom` et `prenom` (1 et 2) servent au rapprochement Supabase des signatures et des annulations. Un décalage fausse simultanément les statuts, les destinataires des mails et les rapprochements de signature — sans erreur, sans entrée au journal, sans trace dans le rapport de synchro.

**Portée actuelle** : latent. Il n'existe aujourd'hui qu'un seul Google Form, celui de `Feuille 1`, et ses 13 questions correspondent aux indices 0-12 de `suivi.COL`. Le défaut se déclenchera à la première formation dotée d'un formulaire différent — ou au premier remaniement du formulaire existant.

**Proposition** : en tête de `importer_inscriptions.py`, comparer `reponses[0]` à la ligne 1 de l'onglet de suivi (`'<onglet>'!A1:M1`) et interrompre avec un message explicite en cas d'écart. Ce contrôle ne nécessite aucune constante partagée entre le script et `app.py`, et transforme une corruption silencieuse en échec visible dans le rapport de synchro.

### Correction appliquée — 01/08/2026

`importer_inscriptions.py` : ajout de `import sys` (l. 4) et d'un contrôle `verifier_entetes()` (l. 20-80), appelé **avant** toute lecture des réponses et toute écriture.

**Argument décisif qui a fait retenir le blocage plutôt que le simple avertissement** : le dédoublonnage (`importer_inscriptions.py:32`, aujourd'hui l. 93) filtre sur l'horodateur. Un import corrompu rendrait ces horodateurs « connus » — après correction du formulaire, une relance les ignorerait, et les lignes fausses resteraient en place définitivement, sauf suppression manuelle ligne à ligne. **Un import corrompu ne se répare pas en relançant : il s'auto-verrouille.**

Décisions de conception :

- **Comparaison normalisée** (espaces compressés, casse ignorée) et non stricte. Obligatoire : le formulaire renvoie `'Prénom '` et `'Adresse mail '` avec une espace finale, alors que `ENTETES_FORM` (`app.py:179-202`, écrit lors de la correction Feuille 1) ne les porte pas. Une comparaison stricte aurait bloqué tout import sur une session créée après cette correction — un faux positif garanti.
- **Lecture du formulaire sur `A1:Z1`** et non `A1:M1`, pour détecter aussi les questions ajoutées au-delà de la colonne M, invisibles autrement.
- **Blocage sur tout écart**, y compris une question ajoutée en fin de formulaire alors que A:M resterait aligné. Ses réponses seraient perdues silencieusement, la lecture s'arrêtant à M. Toute modification du formulaire doit être un acte conscient.
- **Diagnostic sur `stderr`**, résumé en dernière ligne. `dfm.py:52-62` ne lit que `stderr` pour une étape en échec : `details` retient les 6 dernières lignes, `cause` la dernière contenant « Error »/« error », sinon la dernière tout court. Aucune ligne du message ne contient ce mot, donc `cause` est toujours le résumé final.
- **Pas d'écriture au journal depuis le script.** En synchro automatique, `dfm.py` tourne toutes les 5 minutes : un formulaire désaligné produirait une entrée toutes les 5 minutes. L'anti-répétition de B3 vit en mémoire dans le processus Flask et ne s'applique pas à un script relancé à neuf. Une trace durable au journal reste possible, mais demande son propre garde-fou de fréquence.

**Effet de bord accepté explicitement** : un blocage à l'étape 1 arrête les onze étapes suivantes via `dfm.py:73` — conventions, factures, attestations comprises, y compris pour les praticiens déjà correctement importés. C'est le défaut **B1**, pas celui-ci. Décision de l'utilisateur : ne pas affaiblir ce contrôle pour le contourner, mais traiter la résilience de `dfm.py` séparément. Une chaîne qui s'arrête est un problème visible ; un import corrompu ne l'est pas.

**Vérifié sur les données réelles**, script tronqué après l'appel pour qu'aucun import ne puisse avoir lieu :

- en-têtes actuels conformes → `-> En-tetes conformes (13 colonnes).`, code retour 0
- onglet de suivi introuvable → code retour 1, message explicite sur `stderr`
- divergence réelle provoquée (comparaison au tableau `Journal`) → code retour 1, `cause` = `Import interrompu : 13 colonne(s) divergente(s) sur usures-nov26, la premiere en colonne A. Aucune ligne importee. Verifie l'ordre des questions du Google Form.` (162 caractères, sous la limite de 220), et `details` listant les colonnes fautives avec attendu / trouvé.

---

# C. Ce qui est incohérent

## C1. Six phrases du journal perdent le nom de la session

**Où** : `journal.py:87-92` puis `journal.py:110-121` — les mêmes clés du dictionnaire `PHRASES` sont redéfinies, les secondes écrasent les premières :

| clé | ligne 87-92 | ligne 110-121 (celle qui gagne) |
|---|---|---|
| `Convention PDF générée` | `La convention signée de {p} a été générée · {f}` | `… a été générée` |
| `Mail de confirmation envoyé` | `Confirmation d'inscription envoyée à {p} · {f}` | `… à {p}` |
| `Mail file d'attente envoyé` | `Mail de file d'attente envoyé à {p} · {f}` | `… à {p}` |
| `Facture générée` | `Facture de {p} générée · {f}` | `… générée` |
| `Facture envoyée` | `Facture envoyée à {p} · {f}` | `… à {p}` |
| `Attestation envoyée` | `Attestation envoyée à {p} · {f}` | `… à {p}` |

**Conséquence utilisateur** : dans `/journal`, ces six types d'événements n'indiquent plus de quelle formation ils relèvent. Avec plusieurs sessions, le journal devient illisible.

**Proposition** : supprimer les six lignes 110-121 (les premières sont les bonnes).

### Complément relevé à l'application — 01/08/2026

Il y avait **sept** doublons, pas six. Le septième, `"Présence pointée"` (lignes 93 et 122), avait échappé à l'audit : `pyflakes` ne signale que les clés répétées *avec des valeurs différentes*, or les deux valeurs étaient identiques. Sans effet fonctionnel, mais retiré également sur décision de l'utilisateur — une clé définie deux fois est un piège dès que l'une des deux occurrences est modifiée sans l'autre.

**Correction appliquée** : sept lignes retirées (110, 111, 112, 118, 119, 121, 122). Vérifié après écriture : 54 clés, 0 doublon, et les sept libellés concernés portent bien leur `· {f}`.

---

## C2. Des événements de session sont rattachés à la mauvaise session

`journal.ecrire` (`journal.py:30`) a pour signature `(type_action, praticien="", detail="", montant="", code_session="")` et retombe sur `S["code"]` — donc `usures-nov26` — quand `code_session` est omis (`journal.py:38`).

Or il est omis là où il compte :

| ligne | événement |
|---|---|
| `app.py:455` | Émargement signé reçu |
| `app.py:497` | Inscriptions clôturées |
| `app.py:605` | Session supprimée |
| `app.py:1677` | Renvoi groupe |
| `app.py:2272` | questionnaire envoyé automatiquement |
| `app.py:3340` | Émargement signé délié |

Et `app.py:1809` est un cas à part :

```python
journal.ecrire("Questionnaire " + quoi + (" ouvert" if etat else " fermé"), "", code)
```

`code` atterrit dans le paramètre **`detail`**, pas `code_session`.

**Conséquence utilisateur** : l'ouverture d'un questionnaire de la session B apparaît dans le journal avec le code de session affiché comme texte de détail, rattachée à la session A. Le filtre par session dans `/journal` ne les retrouve pas.

**Proposition** : ajouter `"", code` en fin d'appel pour les six premiers ; corriger `app.py:1809` en `journal.ecrire(..., "", "", "", code)`.

---

## C3. « 12 derniers mois » n'a aucun effet

**Où** :
- `parametres.py:51-52` propose les valeurs `m3`, `m6`, `m12`, `tout`
- `app.py:2584-2592` (`_qd_periode_bornes`) reconnaît `m3`, `m6`, **`an1`** — et retombe sur « Depuis le début » pour tout le reste

**Conséquence utilisateur** : choisir « 12 derniers mois » dans les paramètres affiche en réalité tout l'historique, avec le libellé « Depuis le début » — sur les écrans Règlements, Conventions et Questionnaires.

**Proposition** : aligner sur `m12` dans `_qd_periode_bornes`.

### Diagnostic rectifié au moment de l'application — 01/08/2026

**Le diagnostic ci-dessus était faux sur le mécanisme, et la correction proposée aurait cassé un écran qui fonctionnait.**

Chaîne réelle, tracée avant écriture :

- `_qd_periode_bornes` n'est atteint que par `/questionnaires/bilan?periode=X` et `/questionnaires/bilan/formation/<code>?periode=X`
- la valeur vient de `questionnaires.html:184`, qui lit le sélecteur `#qq_per`
- les options de ce sélecteur étaient `""`, **`an1`**, `m6`, `m3`

`an1` était donc la valeur **vivante** : choisir « 12 derniers mois » dans l'écran Questionnaires fonctionnait. Passer `_qd_periode_bornes` à `m12` seul aurait fait arriver `an1` sans correspondance, avec repli silencieux sur « Depuis le début ».

Le défaut réel : le gabarit et le paramètre ne parlaient pas le même vocabulaire. Les options `m6` et `m3` portaient le marqueur `selected`, mais `""` et `an1` ne pouvaient pas l'avoir puisque `parametres.py:51-52` propose `tout` et `m12`. **Deux des quatre valeurs de `periode_defaut` étaient donc inapplicables sur cet écran**, pas seulement `m12`.

Contrairement à ce qu'affirmait le diagnostic initial, `conventions.html` et `reglements.html` n'étaient pas concernés : ils emploient déjà `m12` et filtrent en JavaScript côté client, sans passer par `_qd_periode_bornes`.

**Correction appliquée** — trois lignes, deux fichiers :

- `app.py:2621` : `if periode == "an1":` → `if periode in ("m12", "an1"):`, pour que les liens `?periode=an1` déjà en circulation continuent de fonctionner
- `templates/questionnaires.html:58-59` : `value=""` → `value="tout"` et `value="an1"` → `value="m12"`, chacune assortie du marqueur `{{ " selected" if periode_defaut == ... }}`

Comportement préservé : avec `value="tout"`, `questionnaires.html:185` construit `?periode=tout`, et `_qd_periode_bornes("tout")` retombe sur `return "", "Depuis le début"` — résultat identique à l'ancien `value=""` qui n'envoyait aucun paramètre.

Vérifié après écriture : les quatre valeurs (`tout`, `m12`, `m6`, `m3`) pré-sélectionnent chacune l'option correspondante, et une seule.

---

## C4. Neuf réglages sont modifiables et lus par personne

Vérifié par recherche sur l'ensemble du code et des gabarits :

| réglage (`parametres.py`) | lu quelque part ? |
|---|---|
| `releve_heures` (l. 34) | **non** |
| `envois_auto_autorises` (l. 46) | **non** |
| `lignes_tableau` (l. 54) | **non** |
| `mode_sombre` (l. 57) | **non** |
| `fuseau` (l. 60) | **non** |
| `format_date` (l. 66) | **non** |
| `devise` (l. 70) | **non** |
| `conservation_journal` (l. 74) | **non** |
| `conservation_reponses` (l. 77) | **non** |
| `conservation_sessions` (l. 80) | **non** |

Cas voisin : `capacite_defaut` — la fonction `_par_capacite()` (`app.py:4298`) existe mais **n'est jamais appelée**. La création de session utilise `FORMATIONS[formation].get("places_max", 14)` (`app.py:299`).

**Conséquence utilisateur** : l'écran Paramètres promet des comportements qui n'existent pas. `envois_auto_autorises` est le plus trompeur : son libellé annonce « Si vous décochez, DFM demandera toujours confirmation avant d'envoyer un mail programmé » — décocher ne change rien, `_q_auto` envoie sans demander.

**Proposition** : soit brancher, soit retirer du `SCHEMA`. Le minimum est de traiter `envois_auto_autorises` dans `_q_auto` (`app.py:2252`), qui envoie de vrais mails.

---

## C5. Les questionnaires de satisfaction personnalisés ne sont jamais dépouillés

`app.py:1778` publie bien le modèle propre à la formation :

```python
"satisfaction": Q.satisfaction_pour(fcode),
```

Mais **tous** les points de lecture utilisent la trame par défaut en dur :

| ligne | code |
|---|---|
| `app.py:1862` | `modele = Q.SATISFACTION if quoi == "satisfaction" else Q.froid_pour(fcode)` — asymétrie flagrante avec « froid » juste à côté |
| `app.py:2294`, `2298` | `_qd_axes` boucle sur `Q.SATISFACTION["notes"]` |
| `app.py:3237` | `_ap_dossier` idem |

Or l'éditeur attribue aux modèles personnalisés des identifiants pris dans `_ID_NOTES` (`app.py:3344-3345`), qui va jusqu'à `s30`.

**Conséquence utilisateur** : on crée un questionnaire de satisfaction sur mesure, les participants y répondent, et `note_satisfaction` reste vide dans le suivi ; les axes du bilan sont tous à « — ». Les réponses sont bien dans Supabase mais aucun écran ne les voit.

**Proposition** : remplacer les trois `Q.SATISFACTION` par `Q.satisfaction_pour(fcode)` et propager `fcode` dans `_qd_axes` et `_ap_dossier`.

---

## C6. « Profils OF » ne change ni les mails ni les documents

`profil.py` n'est importé nulle part hors de `app.py` (vérifié sur l'ensemble des fichiers).

`COMMUN` n'est alimenté que par `parametres.json`, via `sessions.py:107-120`, et sur sept clés techniques uniquement : `sheet_suivi`, `url_signature`, `logo_id`, `rib_id`, `dossier_conventions`, `dossier_signees`, `template_facture`.

Tout le reste — `organisme`, `marque`, `formateur`, `signature_mail`, `iban`, `bic`, `mail_contact` — reste sur les valeurs codées en dur de `sessions.py:9-16`. Or c'est exactement ce que lisent `mails.contexte` (`mails.py:350-356`), `_mail_relance` (`app.py:1083-1087`) et tous les scripts d'envoi.

**Conséquence utilisateur** : basculer d'organisme change la couleur de l'interface et les contrôles de complétude (`_of_garde`), mais les mails partent toujours signés « Franck Moyal, Smileclub Formations » avec l'IBAN de SAS LBS FORMATION, et les conventions portent la même raison sociale. Deux organismes, un seul jeu de documents.

Pire : `envoyer_facture.py:42` et `envoyer_attestation.py:45` inscrivent « Franck Moyal, Smileclub Formations » **en dur dans le HTML**, hors de tout modèle.

**Proposition** : étendre la boucle de `sessions.py:112-119` aux clés d'identité en lisant `profil.charger()` plutôt que `parametres.charger()` — c'est le point d'injection qui existe déjà, une seule fonction à modifier.

---

## C10. L'IBAN et le SIRET sont écrits en dur dans une dizaine de fichiers de code

> Ajouté le 01/08/2026, relevé en traitant B8. **Corrigé le 01/08/2026** — identité lue depuis le profil de l'organisme. À traiter avec **C6**, dont c'est le même symptôme.

Un `.gitignore` protège les fichiers de données. Il ne peut rien contre des valeurs inscrites dans le code source lui-même :

| Fichier | Contenu en dur |
|---|---|
| `sessions.py:13-14` | IBAN et BIC, dans `COMMUN` |
| `app.py:1086-1087` | IBAN et BIC, en valeurs de repli du mail de relance |
| `mails.py` | IBAN, en repli |
| `envoyer_rappel.py` | IBAN |
| `relancer.py` | IBAN |
| `profil.py` | IBAN et SIRET, en exemples du `SCHEMA` |
| `creer_template_facture.py` | SIRET |
| `maquettes/DFM_parametres.html`, `maquettes/Smileclub_page_choix_paiement.html` | SIRET, IBAN |
| `.anciennes/` | 66 fichiers avec l'IBAN, 3 avec le SIRET |

Un IBAN n'est pas un secret au sens strict — il figure sur les factures et dans les mails de règlement. Le problème n'est pas la confidentialité, c'est **l'emplacement**.

**Conséquence utilisateur** : c'est exactement le même défaut que **C6**. Les données d'identité de l'organisme — raison sociale, IBAN, BIC, SIRET, signature des mails — vivent dans le code au lieu de vivre dans le profil. D'où le constat de C6 : basculer d'organisme change la couleur de l'interface, mais les mails partent toujours avec la même signature et le même IBAN. Tant que ces valeurs sont dans `sessions.py` et dans les scripts, aucun changement de profil ne peut les atteindre.

À quoi s'ajoute, dans deux cas, une valeur en dur directement dans le corps HTML des mails, hors de tout modèle : `envoyer_facture.py:42` et `envoyer_attestation.py:45` signent « Franck Moyal, Smileclub Formations » en clair.

**Proposition** : traiter avec C6. Le point d'injection existe déjà — `sessions.py:107-120` (`_appliquer_parametres`) recopie sept clés techniques depuis `parametres.json` vers `COMMUN`. Il suffit d'étendre le même mécanisme aux clés d'identité en lisant `profil.charger()`. Les valeurs en dur deviennent alors de simples replis, et la bascule d'organisme prend effet partout.

---

## C11. Les modèles Google Docs et Slides portent l'identité de l'organisme en dur

> Ajouté le 01/08/2026, relevé en appliquant C6. **Corrigé le 01/08/2026** — modèles Google balisés, bascule effectuée. Nécessite une intervention manuelle de l'utilisateur dans les modèles, plus un ajout de balises dans trois scripts.

Le branchement du profil (C6) ne touche que le code Python. Les conventions, factures et attestations sont produites en copiant des **modèles Google**, dont le contenu échappe entièrement à DFM. Inspection du 01/08/2026 :

**Modèle convention — « Template Convention USURES »** (`FORMATIONS["usures"]["template_convention"]`)
Balises reconnues : `{{nom_prenom}}`, `{{date_formation}}`, `{{date_du_jour}}`, `{{tarif}}`, `{{signature_praticien}}`.
En dur : numéro de déclaration `11756577975`, SIRET `98857297000016`, `SAS LBS Formation`, `4 rue Joseph Granier 75007 Paris`, `smileclubformations@gmail.com`, `docteur Franck Moyal`, `LBS Formations - Dr. Franck MOYAL`.

**Modèle attestation — « Template CERTIFICAT USURES »** (Google Slides)
Balise reconnue : `{{dates}}`. En dur : `Dr Franck MOYAL`.

**Modèle facture — « Template Facture »** (`COMMUN["template_facture"]`)
Balises reconnues : dix, dont `{{numero_facture}}`, `{{tarif}}`, `{{date_paiement}}`.
En dur : `SAS LBS FORMATION`, `4 rue Joseph Granier, 75007 Paris`, SIRET `98857297000016`, déclaration `11756577975`.

**Conséquence utilisateur** : basculer d'organisme change désormais les mails, mais **pas** les documents contractuels. Une convention émise sous le profil DSF porterait toujours la raison sociale, le SIRET et l'adresse de SAS LBS FORMATION.

**Point à traiter en priorité** : le numéro de déclaration `11756577975` figure dans le modèle de convention et dans celui de facture, alors que le profil de l'organisme porte `en constitution` — l'utilisateur a indiqué le 01/08/2026 ne pas encore l'avoir obtenu de la préfecture. Toute convention générée depuis ce modèle affirme donc un numéro d'enregistrement que l'organisme ne détient pas, sur une pièce contractuelle signée. À vérifier et corriger dans le modèle avant toute nouvelle génération.

**Proposition** : remplacer les mentions en dur par des balises dans les trois modèles, et ajouter les entrées correspondantes aux dictionnaires `remplacements` de `generer_convention_signee.py:60-65`, `generer_factures.py:69-80` et `generer_attestations.py:63-68`. Les valeurs viennent alors de `COMMUN`, donc du profil.

---

## C12. Les attestations s'accumulent en doublons dans le Drive

> Ajouté le 01/08/2026, relevé en traitant A4. **Corrigé le 02/08/2026** — mise à jour du contenu, identifiant stable ; exemplaires surnuméraires signalés et non supprimés.

**Où** : `generer_attestations.py:75-78`

```python
pdf = drive.files().create(
    body={"name": f"Attestation - {nom_prenom}.pdf", "parents": [dossier]},
    media_body=media, fields="id",
).execute()
```

Le PDF est créé sans que les versions antérieures du même nom soient recherchées ni retirées. Seule la copie Slides temporaire est supprimée (ligne 80).

**Constaté** : le dossier `Attestations` contient **deux** fichiers `Attestation - Bruce WAYNE.pdf`. Le lien enregistré dans le suivi ne désigne que le dernier ; l'autre reste orphelin.

**Conséquence utilisateur** : encombrement du Drive, et ambiguïté sur la pièce faisant foi si l'on parcourt le dossier à la main plutôt que par le lien du suivi. Sans gravité tant qu'on passe par l'application, gênant lors d'un contrôle où l'on ouvre le dossier directement.

Le garde-fou `not l["attestation_le"]` (l. 22) empêche normalement une seconde génération pour la même personne : les doublons viennent des cas où cette colonne a été vidée, ou d'exécutions antérieures à sa mise en place.

**Proposition** : appliquer le même traitement qu'à `generer_emargement.py` lors de la correction A12b — chercher un fichier existant du même nom dans le dossier et **remplacer son contenu** plutôt que d'en créer un second. L'identifiant reste stable, donc le lien déjà enregistré ou partagé continue de fonctionner, et aucun orphelin ne s'accumule.

---

## C18. Les pièces jointes du rappel J-20 sont perdues à l'enregistrement

> Diagnostiqué puis **corrigé le 02/08/2026** (`app.py.avant-C18`). Aller-retour vérifié : 3 pièces envoyées sur 5 champs → 3 enregistrées, dont un lien converti en identifiant ; une pièce inexploitable → refus, formation non créée.

Mécanisme réel, établi sur pièces :

1. **Le dépôt fonctionne.** Le glisser-déposer / bouton Importer appelle `/deposer-document`, qui téléverse réellement le fichier dans le dossier Drive `Templates` et renvoie son identifiant ; le champ reçoit le lien (`formation_creer.html:696-724`). Les fichiers déposés **sont dans le Drive**, orphelins mais intacts.
2. **La relecture fonctionne.** `remplirEdition` sait redistribuer une liste `pieces_rappel` dans les cinq champs.
3. **La perte est à l'enregistrement.** Le gabarit a **cinq** `<input name="pieces_rappel">`, mais la route lit `d.get("pieces_rappel")` — qui ne renvoie que **le premier** — puis le découpe sur `\n` : vestige d'un design à un seul `<textarea>`. Les lignes 2 à 5 sont jetées à chaque enregistrement. (`app.py:188` et `:210`)

**Correctif appliqué** : `request.form.getlist("pieces_rappel")` aux deux endroits (la route POST `/formations/nouvelle` sert aussi la modification : les deux cas sont couverts). Les quatre autres documents de l'étape (programme, accès, modèles de convention et d'attestation) sont des champs uniques : **non touchés**, vérifié dans `formations.json`.

**Dégâts constatés (inventaire Drive du 02/08/2026)** — le défaut avait déjà frappé, et pas seulement la Masterclass :

- **Usures a perdu 3 de ses 4 pièces J-20** lors d'une réouverture de fiche le 01/08 (journal : « Formation modifiée », 22:32 et 22:52). Seul `05-Piskorski.pdf` subsiste. Les trois fichiers sont intacts dans le dossier Drive `envoi J-20` et leurs identifiants figurent dans les valeurs d'origine de `sessions.py` : `ARTICLE LFD frontwing.pdf`, `LFD 186_focus composites_ABOU.pdf`, `modalités d'accès PDF.pdf`. **Restauration proposée, non appliquée** (touche Usures).
- Six PDF orphelins dans `Templates` (deux séries identiques, 01/08 19:47 et 02/08 06:01) : ce sont des **doublons** des pièces J-20 d'Usures, téléversés lors des tentatives de dépôt. Les originaux n'ont jamais quitté `envoi J-20` : rien à relier, ces six copies peuvent être mises à la corbeille.

**Restauration effectuée le 02/08/2026** (`formations.json.avant-RESTAURATION`) : les 4 pièces d'Usures rétablies depuis le littéral d'origine de `sessions.py`, lu par analyse syntaxique et non ressaisi ; aucune autre clé de la fiche modifiée, fiche `masterclass` intacte, les 4 fichiers vérifiés sains dans Drive. Les 6 doublons de `Templates` mis à la corbeille après contrôle de non-référence sur 13 fichiers de configuration.

**Anomalie de rattachement, sans rapport avec C18** : `masterclass.template_attestation` et `usures.template_attestation` pointent sur **le même fichier**, `Template CERTIFICAT USURES — BALISE`. Le modèle `Template CERTIFICAT MASTERCLASS — BALISE` est orphelin. Une attestation Masterclass sortirait aujourd'hui au modèle d'Usures. Saisie à corriger dans la fiche, aucun code en cause.

---

## C19. Aucun contrôle ne signale un modèle de document partagé entre deux formations

> Ouvert le 02/08/2026, à la suite de la découverte ci-dessus. **Corrigé le 02/08/2026** — avertissement de partage à l'enregistrement + contrôle de cohérence du nom de fichier.

`masterclass.template_attestation` et `usures.template_attestation` ont pointé plusieurs jours sur le même fichier, `Template CERTIFICAT USURES — BALISE`, alors qu'un modèle Masterclass balisé existait, orphelin. Une attestation Masterclass serait sortie au modèle d'Usures.

**Ce défaut échappe par construction à tous les verrous d'A1.** Ceux-ci garantissent qu'on lit et écrit dans la bonne session ; ici la fiche déclare elle-même le mauvais modèle, et la chaîne l'applique fidèlement. Aucun appariement session/onglet ne peut le détecter : l'erreur est dans la donnée de référence, pas dans son acheminement.

**Contrôle proposé** — un avertissement, jamais un blocage : deux formations peuvent légitimement partager un modèle (une convention commune, par exemple).

- à l'enregistrement d'une fiche : signaler qu'un modèle est déjà utilisé par une autre formation, en la nommant ;
- sur l'écran Modèles : marquer d'un tag « partagé par N formations », à côté des tags orphelin / non utilisée existants ;
- cas le plus parlant : un modèle porte le nom d'une formation (« CERTIFICAT USURES ») et est rattaché à une autre. Un rapprochement entre le nom du fichier — que `/verifier-document` sait déjà lire — et le nom de la formation attraperait précisément l'erreur commise ici.

---

## C4 (suite). Les six réglages encore muets — ce qu'ils coûteraient

> Mis à jour le 02/08/2026. Quatre des dix réglages sont désormais lus. Les six autres restent inertes, **volontairement** : voici pourquoi, pour que la décision soit prise en connaissance de cause plutôt que par oubli.

| Réglage | Pourquoi il n'a pas été branché |
|---|---|
| `format_date` | `suivi.aujourdhui()` **écrit** ses dates dans le Sheet. Changer le format produirait des colonnes mélangeant deux écritures, et `_qd_periode_bornes` ne saurait plus les relire. À traiter comme un réglage d'**affichage seul**, jamais d'écriture — chantier à part. | **Décision du 02/08/2026 : chantier à part, affichage seulement, jamais l'écriture.**
| `fuseau` | N'a d'effet que si DFM tourne un jour sur un serveur distant. En local, l'horloge de la machine fait foi. Valeur nulle aujourd'hui. |
| `lignes_tableau` | Touche une dizaine d'écrans et leur filtrage client. Coût réel, gain faible tant que les volumes restent ceux d'un organisme. |
| `conservation_journal`, `conservation_reponses`, `conservation_sessions` | Les brancher signifierait **supprimer automatiquement des données** : entrées de journal, réponses de participants, sessions archivées. Un défaut dans une telle purge est irréversible. Recommandation : en faire des durées **déclarées** (registre RGPD, export de configuration) et, si une purge est un jour souhaitée, la construire comme une action manuelle avec aperçu de ce qui serait supprimé — jamais comme un automatisme. | **Décision du 02/08/2026 : ce sont des durées déclarées, pas des purges. Les trois libellés et l'intitulé de section ont été reformulés en ce sens (`parametres.py.avant-CONSERVATION`) — l'ancienne rédaction laissait croire qu'une purge s'exécutait.**

`_par_capacite()` reste défini et jamais appelé (relève de C7).

---

## C7. Code mort et logiques dupliquées

### `generer_convention.py` — 125 lignes, appelé par rien

Ni `dfm.py`, ni `app.py` ne le lancent. Identifiants figés en dur, indépendants de `sessions.py` :

```python
SHEET_ID = "1ohUbh_mYqPBTJ5Sa32eXzV7flDsY7sp97ykyKwbk9h8"   # l.4
TEMPLATE_ID = "11Tctc4eM3pAR88vsZwPJvlF39FUN3gFyLLNXUgXefLg" # l.5
TARIF = "975"                                                # l.6
NOM_FORMATION = "Usures"                                     # l.8
CODE_SESSION = "nov26"                                       # l.9
```

Il ne traite en outre que **la première** inscription confirmée (lignes 38-42). C'est la version pré-Supabase de `generer_convention_signee.py`.

**À supprimer** : sa présence laisse croire que la convention non signée est produite quelque part, alors que le pipeline ne génère que la convention signée.

### `preparer_onglet.py` — 74 lignes, appelé par rien, avec une colonne périmée

> Ajouté le 01/08/2026. **Non corrigé.** À supprimer avec `generer_convention.py`.

Ni `dfm.py`, ni `app.py`, ni aucun autre script ne le lancent. Identifiant de Sheet en dur (`preparer_onglet.py:4`), indépendant de `sessions.py` et de `parametres.json`.

Surtout, sa liste `COLONNES_SUIVI` (lignes 6-22) est restée à une version antérieure du suivi :

- elle contient **`rappel_j15_le`**, colonne qui n'existe plus : `suivi.COL` la nomme `rappel_le` (`suivi.py:19`) ;
- elle s'arrête à `attestation_le`, soit 15 colonnes, alors que `suivi.COL` en compte 48.

Le script ajoute (lignes 54, 63-68) toute colonne de sa liste absente de la ligne 1 de l'onglet cible, **à la suite des colonnes existantes**.

**Conséquence utilisateur si quelqu'un le lance** : sur un onglet créé par l'application, il n'en trouverait qu'une seule manquante — `rappel_j15_le` — et l'ajouterait en colonne AW, après `note_froid`. Une colonne parasite qu'aucun code ne lit ni n'écrit, et qui décale la lecture si un jour la plage est étendue au-delà de AV. Il écrirait de surcroît dans le Sheet codé en dur ligne 4, quel que soit le profil ou le paramétrage actifs.

**Proposition** : supprimer le fichier. Le rôle qu'il tenait est assuré depuis par la création de session (`app.py:296-305`), qui construit les 48 en-têtes depuis `suivi.COL` et `ENTETES_FORM`.

### Identifiant de question en dur

`app.py:2806` → `_qd_nombre((r.get("reponses") or {}).get("s09"))`, alors que 500 lignes plus haut (`app.py:2310`) le même calcul passe par `Q.SATISFACTION["recommandation"]["id"]`. Si l'identifiant change, la répartition promoteurs/passifs/détracteurs du bilan tombe silencieusement à zéro pendant que le NPS affiché juste à côté reste juste.

### Même nom de champ, deux sens

`app.py:2711` → `"facture_le": (l.get("facture_envoyee_le") or "")[:10]`

Sur la fiche de session, le champ nommé `facture_le` contient la date d'**envoi** ; sur `/reglements` (`app.py:1533`) le même nom contient la date d'**émission**.

### Cinq scripts CLI refont ce que l'application fait déjà

| script | équivalent web |
|---|---|
| `relancer.py` | `/session/<code>/relance` |
| `saisir_reglement.py` | `/session/<code>/reglement` |
| `valider_annulation.py` | `/session/<code>/annulation` |
| `promouvoir_attente.py` | `/session/<code>/promotion` |
| `relever_emargement.py` | `/session/<code>/emargement` |

Les règles ont divergé. Exemple concret : la route web refuse un second règlement (`app.py:690`), le script CLI ne vérifie rien. Aucun n'est appelé par le pipeline ; ils ne sont dangereux que si quelqu'un les lance à la main.

### Résidus dans `templates/`

`formations.html.safe`, `session.html.safe`, `sessions.html.safe`, `editeur_mail.AVANT_NETTOYAGE`. Inertes (Jinja ne charge que les noms explicites), mais ils rendent les recherches dans le dossier trompeuses.

---

## C8. L'éditeur de mails ne couvre que 2 des ~10 mails envoyés

`mails.USAGES` (`mails.py:5-12`) déclare `signature` et `confirmation`. Ce sont les seuls réellement branchés (`envoyer_mail_signature.py:42`, `envoyer_mail_confirmation.py:41`).

Écrits en dur dans le code, non modifiables depuis l'interface :

| mail | emplacement |
|---|---|
| rappel J-20 | `envoyer_rappel.py` |
| facture | `envoyer_facture.py:29-44` |
| attestation | `envoyer_attestation.py:29-47` |
| file d'attente | `envoyer_mail_attente.py` |
| annulation | `app.py:911-927` |
| relance signature / règlement | `app.py:1114-1141` |
| envoi groupé | `app.py:1571-1589` |
| questionnaires | `app.py:1984-2001` |
| récapitulatif pédagogique | `app.py:3077-3121` |

**Conséquence utilisateur** : l'écran Modèles laisse penser que la messagerie est paramétrable ; en pratique, modifier huit mails sur dix suppose d'éditer du Python. Ce n'est pas un bug, mais c'est l'écart le plus large entre ce que l'interface promet et ce que le code fait.

> **Traité le 02/08/2026 — options A + C retenues par l'utilisateur.**
>
> **A — quatre mails migrés** : file d'attente, rappel J-20, facture, attestation. L'éditeur couvre désormais 6 mails sur 10.
> Méthode : l'enveloppe HTML de `mails.ENVELOPPE` s'est révélée **identique au caractère près** à celle codée en dur dans les quatre scripts ; seul le corps différait. Chaque corps a été découpé mécaniquement en éléments de premier niveau, convertis en blocs `brut` (le seul type qui émet le HTML verbatim), les valeurs remplacées par des balises.
> Preuve : rendu avant (gabarit d'origine évalué sur un contexte fixe) comparé au rendu après (`mails.rendre`) — **identique pour les 4**, à 2 octets près qui sont le saut de ligne d'ouverture et celui de fermeture, situés **hors** de la balise racine et sans effet sur l'affichage. Les objets de mail sont identiques eux aussi.
> Les fragments conditionnels restent dans les scripts et sont injectés par balise, selon le motif déjà employé pour `{{intro}}` : `{{bloc_reglement}}` (rappel), `{{encadre}}` et `{{suite}}` (file d'attente).
> **Limite à connaître** : ces blocs contiennent du HTML brut. Ils sont modifiables bloc par bloc depuis l'éditeur, mais ce n'est pas de la saisie en texte simple. Les convertir en blocs `texte` donnerait une édition plus confortable **au prix d'un rendu légèrement différent** (marges et encodage normalisés au style de la maison) — non fait, puisque l'exigence était l'identité stricte.
>
> **C — les six mails restants sont déclarés** dans `_TP_MAILS_FIGES` et apparaissent sur l'écran Modèles avec la mention « figé dans le code » et « non modifiable ». L'écart demeure, mais il ne trompe plus.
>
> **Reste en dur, signalé sans être corrigé** : l'IBAN et le BIC écrits en toutes lettres dans le bloc de règlement du rappel J-20 (`envoyer_rappel.py`), résidu de C10. Les balises `{{iban}}` et `{{bic}}` produiraient aujourd'hui exactement les mêmes caractères, le profil portant les mêmes valeurs — mais le jour où le profil changera, ce bloc ne suivra pas.

---

## C9. Trois événements ne sont jamais inscrits au journal

> Repéré le 01/08/2026 pendant la correction de A3. **Soldé.** Les trois écritures ont été ajoutées au fil des corrections A3 et A4, sous forme d'appels explicites à `journal.ecrire` plutôt que par substitution de `marquer` à `ecrire` — ce qui évite l'écriture Sheet supplémentaire signalée ci-dessous. Vérifié le 02/08/2026 par analyse syntaxique : `envoyer_facture.py`, `generer_attestations.py` et `envoyer_attestation.py` écrivent chacun au journal. L'entrée « Attestation générée » n'apparaît pas encore dans `/journal` faute d'attestation produite depuis la correction, les traces de test ayant été nettoyées.

`suivi.py` a deux fonctions d'écriture :

- `ecrire(numero, champ, valeur)` (l. 66) — écrit la cellule, rien d'autre
- `marquer(ligne, champ, valeur=None)` (l. 75) — écrit la cellule, recalcule le statut, **et alimente le journal** via `journal.depuis_champ` (l. 80-84)

Trois scripts utilisent `ecrire()` là où `marquer()` serait attendu :

| ligne | champ écrit | entrée de journal prévue mais jamais produite |
|---|---|---|
| `envoyer_facture.py:60` | `facture_envoyee_le` | « Facture envoyée » (`journal.py:14`) |
| `generer_attestations.py:81` | `attestation_le` | « Attestation générée » (`journal.py:15`) |
| `envoyer_attestation.py:63` | `attestation_envoyee_le` | « Attestation envoyée » (`journal.py:16`) |

Les trois libellés existent bien dans `journal.ACTIONS`, avec leur icône, leur phrase dans `PHRASES` et leur style dans `STYLES`. Le déclencheur seul manque.

**Conséquence utilisateur** : `/journal` ne montre jamais l'envoi d'une facture ni le cycle des attestations. Sur un écran conçu comme piste d'audit — et présenté comme tel, avec un réglage « Journal d'activités : durée de conservation » (`parametres.py:74`) — trois étapes contractuelles sur la fin de parcours sont absentes. On ne peut pas prouver depuis DFM qu'une facture a été envoyée.

**Attention avant de corriger** : `marquer()` réécrit aussi la colonne `statut` à partir de `calculer_statut()` (`suivi.py:79`). Or `calculer_statut` (`suivi.py:46-65`) ne connaît ni la facturation ni les attestations : son dernier état est « Reglee ». Substituer `marquer` à `ecrire` sur ces trois lignes est donc sans effet sur le statut affiché — mais cela déclenche une écriture Sheet supplémentaire par praticien. À valider avant application.

**Proposition** : remplacer `suivi.ecrire(...)` par `suivi.marquer(ligne, "<champ>")` aux trois emplacements ; ou, si l'on préfère ne pas toucher au statut, appeler directement `journal.depuis_champ("<champ>", ligne)` après chaque `ecrire`.

---

# Ordre d'attaque proposé

Par rapport gain / risque :

1. **A3** — une ligne dans `envoyer_facture.py:15`. Arrête les renvois de factures en boucle.
2. **C1** — supprimer 6 lignes dans `journal.py:110-121`. **A5** — deux clés dans `app.py:2087-2088`.
3. **B2** — `timeout=600` sur `app.py:4565`. **B3** — déplacer trois lignes dans `app.py:858-864`.
4. **A6** — écrire les deux routes manquantes, ou retirer les appels pour ne pas croire à un automatisme inexistant.
5. **B8** — compléter `.gitignore` **avant** tout `git init`.
6. **A1 / A2** — le chantier de fond : faire circuler le code de session dans les scripts.

**En attendant A1/A2** : ne pas créer de deuxième session en production, et ne pas utiliser le bouton de clôture ailleurs que sur `usures-nov26`.

---

## État du pipeline au moment de l'audit

`derniere_synchro.json` — passage du 31/07/2026 23:13, les 12 étapes en « OK ». À nuancer : la session `usures-nov26` étant datée de novembre 2026, la plupart des étapes sortent immédiatement sans rien faire (rappel J-20 trop tôt, attestations trop tôt). Un « OK » sur les 12 étapes ne prouve donc pas que la chaîne fonctionne — voir **A4**, où une étape inerte est comptée comme réussie.
