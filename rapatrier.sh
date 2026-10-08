#!/bin/bash
# Rapatrie les DONNEES du serveur vers le Mac. Jamais le contraire.
#
# POURQUOI CE SENS UNIQUE. Depuis le 20/08/2026, le serveur detient la verite :
# sessions, inscriptions, factures et journal scelle n'y sont crees que la-bas.
# Le Mac en garde un miroir — et ce miroir est le seul filet reel, puisque la
# sauvegarde quotidienne vit sur la machine qu'elle protege.
#
# CE QUI NE REMONTE PAS. Les secrets (acces.json, scellement.json, smtp.json,
# token.json, credentials.json, config.py) restent ou ils sont. acces.json
# surtout : le rapatrier imposerait au DFM local un mot de passe qui n'a aucune
# raison d'y etre.
#
#     ./rapatrier.sh                  demande confirmation
#     ./rapatrier.sh --sans-question  pour un enchainement automatique
#
set -u
SERVEUR="dfm@163.172.8.49"
DISTANT="/home/dfm/DFM"
GARDES=10
cd "$(dirname "$0")" || exit 1

# LA LISTE BLANCHE, ECRITE UNE SEULE FOIS. Elle sert au rapatriement ET au
# controle qui le suit : deux copies auraient fini par diverger, et le controle
# aurait alors valide un miroir infidele.
REGLES=(
  --exclude=acces.json --exclude=credentials.json --exclude=scellement.json
  --exclude=smtp.json --exclude=token.json --exclude=config.py
  --exclude=*.verrou --exclude=dfm.db --exclude=dfm.db-wal --exclude=dfm.db-shm
  --include=documents/ --include=documents/**
  --include=identite/  --include=identite/**
  --include=profils/   --include=profils/**
  --include=justificatifs/ --include=justificatifs/**
  --include=questionnaires_figes/ --include=questionnaires_figes/**
  --include=.sauvegardes/ --include=.sauvegardes/**
  --include=*.json
  --exclude=*
)

echo
echo "  RAPATRIEMENT DES DONNEES DU SERVEUR"
echo "  ------------------------------------------------------------"

if ! ssh -o ConnectTimeout=15 -o BatchMode=yes "$SERVEUR" true 2>/dev/null; then
  echo "  Le serveur ne repond pas. Rien n'a ete rapatrie."
  exit 1
fi

# 1. DFM NE DOIT PAS TOURNER SUR LE MAC. Remplacer une base pendant qu'un
# processus la lit revient a lui retirer la table sous les coudes : il continue
# avec l'ancienne en memoire et reecrit par-dessus la nouvelle.
# ON NE REGARDE QUE CELUI QUI ECOUTE. « lsof -ti :5001 » remonte aussi les
# processus CONNECTES au port — le navigateur qui a un onglet ouvert en fait
# partie. Le 20/08/2026, cette confusion m'a fait arreter un processus Chrome
# en croyant arreter DFM. « -sTCP:LISTEN » ne retient que l'hebergeur.
if lsof -ti :5001 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "  DFM TOURNE SUR CE MAC (port 5001). Fermez-le d'abord."
  echo "  Rien n'a ete rapatrie."
  exit 1
fi

# 2. CE QUE LE MAC A AUJOURD'HUI, mis de cote avant d'etre remplace.
mkdir -p .miroirs
MARQUE=$(date +%Y%m%d-%H%M%S)
zip -q ".miroirs/avant-$MARQUE.zip" *.json dfm.db 2>/dev/null
ls -1t .miroirs/avant-*.zip 2>/dev/null | tail -n +$((GARDES+1)) | xargs -r rm -f
echo "  Etat precedent mis de cote : .miroirs/avant-$MARQUE.zip"

# 3. UNE COPIE COHERENTE DE LA BASE. Copier dfm.db pendant que DFM ecrit donne
# un fichier a moitie ecrit. sqlite3.backup() prend une photo propre, meme sous
# ecriture — c'est la seule facon correcte de copier une base vivante.
echo "  Photo de la base sur le serveur..."
ssh "$SERVEUR" "cd $DISTANT && venv/bin/python -c \"
import sqlite3
s = sqlite3.connect('dfm.db'); d = sqlite3.connect('/home/dfm/dfm-photo.db')
s.backup(d); d.close(); s.close()\"" || {
  echo "  La photo de la base a echoue. Rien n'a ete rapatrie."
  exit 1
}

# 4. LES DONNEES. Liste blanche, comme pour l'envoi : ce qui n'est pas nomme
# ne descend pas.
echo "  Rapatriement..."
# « --info=stats2 » N'EXISTE PAS DANS RSYNC 2.6.9, celui que livre macOS.
# Constate le 20/08/2026 : rsync s'arretait sur l'option, ne transferait RIEN,
# et le grep qui suivait avalait son message d'erreur. Le script continuait,
# remplacait la base par scp — ce qui suffisait a faire passer le controle des
# scelles — puis annoncait « Le miroir est fidele ». Trois passages de miroir
# n'ont deplace aucun fichier, et rien ne l'a dit.
#
# DEUX LECONS APPLIQUEES ICI : on garde la sortie au lieu de la filtrer a la
# volee, et on REGARDE LE CODE DE RETOUR. Un tube rend le code du dernier
# maillon, jamais celui de rsync.
SORTIE=$(rsync -az --stats "${REGLES[@]}" \
  "$SERVEUR:$DISTANT/" ./ 2>&1)
CODE=$?
if [ $CODE -ne 0 ]; then
  echo "  LE RAPATRIEMENT A ECHOUE (code $CODE). Rien n'a ete remplace."
  echo "$SORTIE" | head -5 | sed 's/^/      /'
  exit 1
fi
echo "$SORTIE" | grep -i "Number of files transferred\|Total transferred file size" | sed 's/^/    /'

# 5. LA BASE, POSEE PROPREMENT. Les fichiers -wal et -shm du Mac appartiennent
# a l'ANCIENNE base : les laisser a cote de la nouvelle, c'est demander a
# SQLite d'appliquer le journal d'une base sur une autre. On les retire.
scp -q "$SERVEUR:/home/dfm/dfm-photo.db" ./dfm-photo.db && {
  rm -f dfm.db-wal dfm.db-shm
  mv -f dfm-photo.db dfm.db
  echo "    base remplacee, journaux perimes retires"
}
ssh "$SERVEUR" "rm -f /home/dfm/dfm-photo.db"

# 6. LE MIROIR EST-IL VRAIMENT FIDELE ? On redemande a rsync ce qu'il resterait
# a transferer. S'il reste quoi que ce soit, le rapatriement n'a pas fait son
# travail — et il vaut mille fois mieux l'apprendre ici que le jour ou l'on
# compte sur ce miroir. C'est ce controle qui manquait le 20/08/2026, quand
# trois passages n'ont deplace aucun fichier en annoncant le contraire.
echo "  ------------------------------------------------------------"
RESTE=$(rsync -an "${REGLES[@]}" --out-format="%n" \
  "$SERVEUR:$DISTANT/" ./ 2>/dev/null | grep -v '/$' | grep -v '^$')
if [ -n "$RESTE" ]; then
  echo "    MIROIR INCOMPLET — il reste des fichiers non rapatries :"
  echo "$RESTE" | head -10 | sed 's/^/        /'
  echo "    Ne comptez pas sur cette copie."
else
  echo "    Tous les fichiers du serveur sont sur ce Mac."
fi

# 7. LE CONTROLE QUI PROUVE QUELQUE CHOSE. Un fichier de la bonne taille ne dit
# rien ; une chaine de scelles qui se verifie, si. Si elle est rompue, la copie
# est inutilisable comme piece d'audit — et il vaut mieux l'apprendre ici.
# LE PYTHON DE DFM, PAS CELUI DU SYSTEME. journal.py tire connexion.py, qui
# tire les bibliotheques Google : hors de l'environnement virtuel, le controle
# echoue pour une raison qui n'a rien a voir avec la fidelite du miroir.
venv/bin/python - <<'PYEOF'
import journal
ok = True
for o in ("dsf", "mon-organisme"):
    f = (journal.verifier(o) or [{}])[0]
    intacte = f.get("intacte")
    ok = ok and intacte
    print("    %-16s %4d entrees, %s" % (o, f.get("entrees", 0),
                                         "chaine intacte" if intacte else "CHAINE ROMPUE"))
print("    " + ("Le miroir est fidele." if ok else
      "MIROIR INUTILISABLE : reprenez .miroirs/ et prevenez avant d'y toucher."))
PYEOF
echo
