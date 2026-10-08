#!/bin/bash
# Envoie le CODE de DFM vers le serveur. Jamais les donnees.
#
# POURQUOI UNE LISTE BLANCHE ET PAS UNE LISTE D'EXCLUSIONS. Le serveur detient
# desormais la verite : sessions, inscriptions, factures, journal scelle
# n'existent que la-bas. Une liste d'exclusions oublierait tot ou tard un
# fichier nouveau — et cet oubli ecraserait des donnees vivantes par la copie
# figee du Mac, sans un message. Ici, ce qui n'est pas nomme ne part pas.
#
#     ./deployer.sh              demande confirmation
#     ./deployer.sh --sans-question   pour un enchainement automatique
#
set -u
SERVEUR="dfm@163.172.8.49"
ADRESSE="https://163-172-8-49.nip.io"
DISTANT="/home/dfm/DFM"
GARDES=10
cd "$(dirname "$0")" || exit 1

# CE QUI PART, ET RIEN D'AUTRE.
REGLES=(
  --exclude=venv/ --exclude=__pycache__/ --exclude=.travail/ --exclude=.DS_Store
  # config.py porte les cles Supabase. C'est un secret : il voyage a la main,
  # une fois, jamais dans un envoi de routine qui pourrait ecraser une cle
  # changee sur le serveur par une cle perimee du Mac.
  --exclude=config.py
  --include=templates/ --include=templates/**
  --include=static/    --include=static/**
  --include=*.py
  --include=requirements.txt
  --exclude=*
)

echo
echo "  ENVOI DU CODE DE DFM VERS LE SERVEUR"
echo "  ------------------------------------------------------------"

if ! ssh -o ConnectTimeout=15 -o BatchMode=yes "$SERVEUR" true 2>/dev/null; then
  echo "  Le serveur ne repond pas. Rien n'a ete envoye."
  exit 1
fi

# 1. TOUT COMPILE-T-IL ? Controle fait ICI, avant que quoi que ce soit parte.
#
# POURQUOI CE CONTROLE EXISTE. Eprouve le 20/08/2026 : un pdf.py casse est
# parti, le service est reste « actif », l'adresse a repondu 200 — et la
# fabrication des PDF etait morte. La plupart des modules de DFM ne sont
# charges qu'au moment de servir : demander a DFM s'il repond ne dit RIEN de
# ce qu'il sait encore faire. Seule la compilation le dit.
CASSES=$(python3 - <<'PYEOF'
import glob, io
ko = []
for f in sorted(glob.glob("*.py")):
    try:
        # compile() verifie la syntaxe SANS rien ecrire. py_compile, lui, veut
        # produire un .pyc : il refuse /dev/null et fait echouer le controle
        # pour une raison qui n'a rien a voir avec le code.
        compile(io.open(f, encoding="utf-8").read(), f, "exec")
    except SyntaxError as e:
        ko.append("%s ligne %s : %s" % (f, e.lineno, (e.msg or "")[:70]))
    except Exception as e:
        ko.append("%s : %s" % (f, str(e).splitlines()[0][:80]))
print("\n".join(ko))
PYEOF
)
if [ -n "$CASSES" ]; then
  echo "  DU CODE NE COMPILE PAS. Rien n'a ete envoye."
  echo "$CASSES" | sed 's/^/      /'
  exit 1
fi
echo "  Tout compile sur le Mac."

# 2. CE QUI CHANGERAIT, avant de changer quoi que ce soit.
CHANGES=$(rsync -an --out-format="%n" "${REGLES[@]}" ./ "$SERVEUR:$DISTANT/" 2>/dev/null \
          | grep -v '/$' | grep -v '^$')
if [ -z "$CHANGES" ]; then
  echo "  Le serveur a deja exactement ce code. Rien a envoyer."
  exit 0
fi
echo "  Fichiers qui vont changer :"
echo "$CHANGES" | sed 's/^/      /'
echo "  ------------------------------------------------------------"
echo "  $(echo "$CHANGES" | wc -l | tr -d ' ') fichier(s). Les donnees du serveur ne sont pas touchees."
echo

if [ "${1:-}" != "--sans-question" ]; then
  read -p "  Envoyer ? (o/n) " REP
  [ "$REP" = "o" ] || [ "$REP" = "O" ] || { echo "  Annule. Rien n'a bouge."; exit 0; }
  echo
fi

# 3. LE POINT DE RETOUR, pris avant l'ecrasement. Sans lui, un envoi qui casse
# DFM le laisse casse : le Mac ne contient plus la version qui marchait.
MARQUE=$(date +%Y%m%d-%H%M%S)
echo "  Point de retour : $MARQUE"
ssh "$SERVEUR" "cd $DISTANT && tar czf ~/deploiements/code-$MARQUE.tgz \
  --exclude=venv --exclude=__pycache__ *.py templates static 2>/dev/null; \
  ls -1t ~/deploiements/code-*.tgz 2>/dev/null | tail -n +$((GARDES+1)) | xargs -r rm -f" || {
  echo "  Le point de retour n'a pas pu etre pris. Rien n'a ete envoye."
  exit 1
}

# 4. L'ENVOI.
echo "  Envoi..."
rsync -a "${REGLES[@]}" ./ "$SERVEUR:$DISTANT/" || {
  echo "  L'envoi a echoue. Le serveur n'a pas ete relance."
  exit 1
}

# 5. ET SUR LE SERVEUR ? Le Mac tourne peut-etre une autre version de Python,
# et un transfert peut abimer un fichier. On redemande sur place.
CASSES_D=$(ssh "$SERVEUR" "cd $DISTANT && venv/bin/python - <<'PYEOF'
import glob, io
ko = []
for f in sorted(glob.glob('*.py')):
    try:
        compile(io.open(f, encoding='utf-8').read(), f, 'exec')
    except SyntaxError as e:
        ko.append('%s ligne %s : %s' % (f, e.lineno, (e.msg or '')[:70]))
    except Exception as e:
        ko.append('%s : %s' % (f, str(e).splitlines()[0][:80]))
print('\n'.join(ko))
PYEOF
" 2>/dev/null)
if [ -n "$CASSES_D" ]; then
  echo "  DU CODE NE COMPILE PAS SUR LE SERVEUR :"
  echo "$CASSES_D" | sed 's/^/      /'
  echo "  RETOUR ARRIERE, sans meme relancer DFM."
  ssh "$SERVEUR" "cd $DISTANT && tar xzf ~/deploiements/code-$MARQUE.tgz"
  echo "  Version precedente retablie. DFM n'a pas ete interrompu."
  exit 1
fi

# 6. LA RELANCE.
echo "  Relance de DFM..."
ssh "$SERVEUR" "sudo systemctl restart dfm"
sleep 8

# 7. DFM REPOND-IL VRAIMENT ? On interroge par l'adresse publique, comme le
# ferait un navigateur — c'est le seul controle qui prouve quelque chose.
CODE=$(curl -s -m 30 -o /dev/null -w "%{http_code}" "$ADRESSE/connexion" 2>/dev/null)
if [ "$CODE" = "200" ]; then
  echo "  ------------------------------------------------------------"
  echo "  DFM repond. Envoi termine."
  echo "  $ADRESSE"
  exit 0
fi

# 8. RETOUR ARRIERE AUTOMATIQUE. Un DFM casse en ligne n'attend pas qu'on
# diagnostique : on remet ce qui marchait, puis on cherche.
echo "  ------------------------------------------------------------"
echo "  DFM NE REPOND PLUS (code $CODE). RETOUR ARRIERE EN COURS."
ssh "$SERVEUR" "cd $DISTANT && tar xzf ~/deploiements/code-$MARQUE.tgz && sudo systemctl restart dfm"
sleep 8
CODE2=$(curl -s -m 30 -o /dev/null -w "%{http_code}" "$ADRESSE/connexion" 2>/dev/null)
if [ "$CODE2" = "200" ]; then
  echo "  Version precedente retablie, DFM repond de nouveau."
  echo "  L'envoi a ete annule : cherchez la cause avant de recommencer."
else
  echo "  LE RETOUR ARRIERE N'A PAS SUFFI (code $CODE2)."
  echo "  Regardez ce que dit DFM :"
  ssh "$SERVEUR" "sudo systemctl status dfm --no-pager -l 2>&1 | tail -20"
fi
exit 1
