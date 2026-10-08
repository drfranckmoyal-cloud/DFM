# Autorisations de Claude sur le projet DFM

Deux reglages travaillent ensemble :

1. **Le mode « Auto »** (dans votre fichier personnel `~/.claude/settings.json`) :
   il supprime les demandes d'autorisation de routine.
2. **Les garde-fous** (dans `.claude/settings.json`, dans les deux dossiers DFM) :
   ils forcent l'arret sur ce qui est dangereux, y compris en mode Auto.

---

## 1. Le mode Auto

Sans lui, Claude vous demande l'autorisation pour presque chaque commande, parce
qu'une liste de commandes autorisees ne peut jamais tout prevoir : il suffit
qu'une commande soit legerement differente (un enchainement, une boucle) pour
qu'elle sorte de la liste.

En mode Auto, un **second modele de securite** examine chaque action avant
qu'elle ne s'execute. Il laisse passer le travail ordinaire et bloque ce qui est
risque : destruction de fichiers qui existaient avant la session, envoi de
donnees sensibles vers l'exterieur, suppressions en masse, etc.

Il est active par defaut dans `~/.claude/settings.json` :

```json
"permissions": { "defaultMode": "auto" }
```

**Attention** : ce reglage ne fonctionne **que** dans le fichier personnel
(`~/.claude/settings.json`). Place dans un fichier de projet, Claude Code
l'ignore volontairement — pour qu'un dossier ne puisse pas s'auto-attribuer ce
mode.

Pour l'activer tout de suite sans redemarrer : selecteur de mode a cote du
bouton d'envoi, choisir **Auto** (dans un terminal : `Shift+Tab`).

---

## 2. Ce qui vous demandera toujours confirmation

Ces regles sont plus fortes que le mode Auto : elles s'appliquent dans tous les
cas.

**Supprimer ou deplacer**
- `rm`, `rmdir`, `mv`, corbeille, modification de fichier en place (`sed -i`),
  `truncate`, `dd`.

**Tous les scripts qui envoient un mail reel**
- `envoyer_facture.py`, `envoyer_attestation.py`, `envoyer_mail_attente.py`,
  `envoyer_mail_confirmation.py`, `envoyer_mail_signature.py`,
  `envoyer_rappel.py`, `relancer.py`, `valider_annulation.py`.

**Tous les scripts qui ecrivent dans Google Sheets ou Drive**
- `generer_attestations.py`, `generer_convention.py`,
  `generer_convention_signee.py`, `generer_emargement.py`,
  `generer_factures.py`, `dupliquer_modeles.py`,
  `importer_inscriptions.py`, `relever_signatures.py`,
  `relever_annulations.py`, `relever_emargement.py`, `promouvoir_attente.py`,
  `cloturer_inscriptions.py`, `saisir_reglement.py`, `pointer_presences.py`,
  `preparer_journal.py`, `preparer_onglet.py`, `preparer_onglet_sessions.py`,
  `ajouter_colonnes.py`, ainsi que `dfm.py` (qui peut appeler tous les autres).
- Idem pour la creation ou la copie de fichiers dans Drive.

## 3. Ce qui est interdit, meme si vous etes devant l'ecran

- `sudo` (commandes administrateur).
- `rm -rf` vise sur `/`, sur `/Users` ou sur votre dossier personnel.

---

## 4. Ce que Claude fait sans demander

Le travail ordinaire : lire les fichiers, les modifier dans `~/Desktop/DFM`,
faire des copies de sauvegarde, afficher des bouts de fichiers, verifier que le
code compile (`python3 verifier.py` controle les 46 fichiers d'un coup),
lancer les scripts qui ne font que lire (`lire_inscriptions.py`,
`etat_session.py`, `voir_journal.py`, `trier_inscriptions.py`,
`test_connexion.py`), et demarrer le site en local (`app.py`).

---

## 5. A savoir

- Le mode Auto **reduit** les demandes, il ne garantit pas la securite. C'est
  un filet, pas une assurance : gardez un oeil sur ce qui a ete fait.
- Le modele de securite consomme des jetons a chaque verification.
- Si une action est bloquee 3 fois de suite, le mode Auto se met en pause et
  Claude recommence a vous demander.

---

## 6. Revenir en arriere

**Redevenir comme avant (Claude redemande tout)** — enlevez la ligne
`"defaultMode": "auto"` de `~/.claude/settings.json`, ou choisissez
**Manuel** dans le selecteur de mode.

**Tout supprimer** :

```bash
rm /Users/franckmoyal/Desktop/DFM/.claude/settings.json /Users/franckmoyal/DFM/.claude/settings.json
```

**Retrouver l'ancienne liste d'autorisations** :

```bash
cp -p /Users/franckmoyal/DFM/.claude/settings.local.json.avant-permissions /Users/franckmoyal/DFM/.claude/settings.local.json
```

**Ne changer qu'un point** — dites-le simplement a Claude en francais.
Dans les fichiers : `allow` = autorise, `ask` = demande, `deny` = interdit.
