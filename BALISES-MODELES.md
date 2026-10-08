# Balises des modèles Google — DFM

Aide-mémoire pour construire un modèle de convention ou de facture directement
balisé, sans phase de correction ensuite. **L'attestation n'entre plus dans ce
cadre** : elle a son propre modèle dans DFM, sans balises — voir plus bas.

Une balise s'écrit exactement `{{nom}}`, en minuscules, sans espace à l'intérieur
des accolades. Elle peut être placée n'importe où : corps, tableau, en-tête de page.
La casse compte : `{{Organisme}}` ne serait **pas** reconnue.

**Toute balise non listée ici reste affichée en clair dans le document généré.**

Dernière mise à jour : 06/08/2026.

---

## Balises d'identité — disponibles dans les trois types de document

Elles viennent du profil de l'organisme actif (écran **Profils OF**). Changer
d'organisme change leur valeur partout, sans retoucher les modèles.

Une valeur absente du profil produit **du vide**, jamais `{{siret}}` en clair.

| Balise | Produit aujourd'hui |
|---|---|
| `{{organisme}}` | SAS LBS FORMATION |
| `{{marque}}` | Smileclub Formations |
| `{{adresse_organisme}}` | 4 rue Joseph Granier, 75007 Paris |
| `{{siret}}` | 98857297000016 |
| `{{numero_declaration}}` | en constitution |
| `{{mention_declaration}}` | Déclaration d'activité : en constitution |
| `{{mention_declaration_longue}}` | Déclaration d'activité : en constitution auprès de la Direction Régionale des Entreprises, de la Concurrence, de la Consommation, du Travail et de l'Emploi (DIRECCTE) |
| `{{formateur}}` | Dr Franck Moyal |
| `{{mail_contact}}` | smileclubformations@gmail.com |
| `{{telephone}}` | 06 27 68 36 17 |
| `{{iban}}` | FR76 1470 7000 0134 2210 2342 695 |
| `{{bic}}` | CCBPFRPPMTZ |

### Les deux balises de déclaration d'activité

Elles portent **leur propre intitulé** et disparaissent **entièrement** quand le
numéro n'est pas renseigné dans le profil. C'est leur intérêt : pas d'intitulé
orphelin sur une pièce contractuelle.

- `{{mention_declaration}}` — forme courte, pour un bloc d'en-tête de facture.
- `{{mention_declaration_longue}}` — ajoute l'autorité d'enregistrement, pour la
  clause des parties d'une convention.

N'utilisez `{{numero_declaration}}` seule que si l'intitulé est déjà écrit à côté
dans le modèle — et sachez qu'alors l'intitulé subsistera même sans numéro.

### Raison sociale ou nom commercial ?

- `{{organisme}}` — la **raison sociale**. À employer dans tout ce qui engage :
  clause des parties, mentions légales, en-tête de facture.
- `{{marque}}` — le **nom commercial**. À employer dans ce qui s'adresse au
  praticien : en-tête de courrier, bloc de signature.

---

## Balises propres à la convention

Remplies par `generer_convention_signee.py`.

| Balise | Produit |
|---|---|
| `{{nom_prenom}}` | Prénom et nom du praticien |
| `{{date_formation}}` | Dates de la formation, telles que saisies à l'inscription |
| `{{date_du_jour}}` | Date de génération du document, format JJ/MM/AAAA |
| `{{tarif}}` | Tarif de la session, en euros, sans symbole |
| `{{signature_praticien}}` | Remplacée par l'**image** de la signature manuscrite |

`{{signature_praticien}}` est traitée à part : la balise est effacée et l'image
insérée à son emplacement, en 120 × 50 points. Placez-la seule sur sa ligne.

---

## Balises propres à la facture

Remplies par `generer_factures.py`.

| Balise | Produit |
|---|---|
| `{{numero_facture}}` | Numéro attribué automatiquement, format `F2026-001` |
| `{{date_facture}}` | Date d'émission, format JJ/MM/AAAA |
| `{{nom_prenom}}` | Prénom et nom du praticien |
| `{{titre_formation}}` | Titre complet de la formation |
| `{{date_formation}}` | Dates de la formation |
| `{{duree}}` | Durée, par exemple « 14 heures » |
| `{{tarif}}` | Montant réellement encaissé ; à défaut, le tarif de la session |
| `{{date_paiement}}` | Date d'encaissement |
| `{{mode_paiement}}` | Mode de règlement ; « virement » si non renseigné |
| `{{reference_paiement}}` | Référence du règlement ; « - » si non renseignée |

Le numéro de facture est calculé à partir des factures déjà émises dans l'année :
ne le composez pas à la main dans le modèle.

---

## L'attestation n'a plus de modèle à baliser

**Depuis le 06/08/2026, l'attestation de fin de formation ne se construit plus
avec des balises.** Il n'y a plus rien à préparer dans le Drive, et le champ
« Modèle d'attestation » d'une fiche formation ne sert plus à rien.

Le modèle est **unique pour toutes les formations** et vit dans DFM :
`templates/attestation.html`. Son en-tête s'ajuste tout seul à l'organisme —
logo, SIRET, numéro de déclaration. Le PDF est fabriqué par Chrome, puis déposé
dans le dossier Drive « Attestations » comme avant.

**Pourquoi.** Chaque formation avait sa présentation Slides pour une seule
raison : le titre de la formation y était écrit en dur. Ces modèles portaient
quatre informations, là où l'article L.6353-1 en exige huit. La durée, la nature
de l'action et les résultats de l'évaluation des acquis manquaient à toutes les
attestations émises jusque-là.

Ce qui figure maintenant sur l'attestation, sans aucune saisie :

| Rubrique | Source |
|---|---|
| Identité du bénéficiaire, civilité | ligne de suivi — « Dr » seulement si la fonction est chirurgien-dentiste |
| En-tête, SIRET, déclaration d'activité, logo, signataire | profil de l'organisme actif |
| Intitulé, public visé, lieu | fiche de formation |
| Dates, journées détaillées, début / fin, durée | `jours.resume()` — la liste des journées réellement travaillées |
| Objectifs, acquis / en cours / à acquérir, scores et progression | modèle de questionnaire et réponses relevées |
| Numéro `AT2026-001` | registre `attestations.json`, un compteur par organisme |

Le numéro est attribué **une fois** et ne change jamais, même si l'attestation
est régénérée : le PDF est remplacé en place dans le Drive, son lien et son
numéro restent ceux du document déjà remis.

Pour modifier la mise en page, on édite `templates/attestation.html` — c'est du
HTML, plus une diapositive.

---

## Ce qui n'est pas disponible

Ces champs existent dans le profil mais n'ont pas de balise. Dites-le si vous en
avez besoin, l'ajout se fait dans `sessions.balises_identite()`.

`forme_juridique` · `capital` · `prefecture_declaration` seule · `tva_franchise` ·
`tva_numero` · `tva_taux` · `site_web` · `pays` · `titulaire_compte` ·
`compte_stripe` · `format_facture` · `couleur`

---

## Vérifier un modèle avant la première utilisation

1. Générer le document sur un praticien de test.
2. Ouvrir le PDF produit et chercher `{{`. Aucune occurrence ne doit subsister.
3. Basculer sur un autre organisme dans **Profils OF**, régénérer, et vérifier que
   l'identité a bien changé.

Le script `dupliquer_modeles.py` permet de baliser un modèle existant sans risque :
il travaille sur des copies, refuse d'agir si le document a changé depuis
l'analyse, et laisse les originaux intacts.
