#!/bin/bash
# Lanceur DFM — double-cliquez ce fichier depuis le Finder.
#
# Il choisit tout seul le bon Python :
#   1. l'environnement isole du dossier (venv), s'il existe ;
#   2. sinon le Python d'Apple, /usr/bin/python3, qui fonctionne toujours.
#
# Il verifie aussi qu'aucun DFM ne tourne deja : fermer la fenetre du Terminal
# n'arrete pas toujours le serveur, et un DFM oublie garderait le port 5001
# occupe, empechant le suivant de demarrer.
#
# Pour arreter DFM proprement : cliquez dans cette fenetre et faites Ctrl + C.

cd "$(dirname "$0")" || exit 1
PORT=5001

# ---------- 1. un DFM tourne-t-il deja ? ----------
DEJA="$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | sort -u)"
if [ -n "$DEJA" ]; then
    echo "───────────────────────────────────────────────"
    echo "  Un DFM tourne deja sur le port $PORT."
    echo "───────────────────────────────────────────────"
    echo
    echo "  Cela arrive quand la fenetre precedente a ete fermee"
    echo "  sans faire Ctrl + C : le serveur continue en arriere-plan."
    echo
    echo "  [1] L'arreter et en demarrer un neuf   (recommande)"
    echo "  [2] Le garder et juste ouvrir le navigateur"
    echo "  [3] Ne rien faire et fermer"
    echo
    read -n 1 -r -p "  Votre choix [1/2/3] : " CHOIX
    echo; echo
    case "$CHOIX" in
        2) open "http://127.0.0.1:$PORT"
           echo "  Navigateur ouvert sur le DFM deja en cours."
           read -n 1 -s -r -p "  Appuyez sur une touche pour fermer..."
           exit 0 ;;
        3) exit 0 ;;
        *) echo "  Arret de l'ancien DFM..."
           for P in $DEJA; do kill "$P" 2>/dev/null; done
           sleep 2
           RESTE="$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | sort -u)"
           for P in $RESTE; do kill -9 "$P" 2>/dev/null; done
           sleep 1
           echo "  Ancien DFM arrete." ;;
    esac
fi

# ---------- 2. quel Python ? ----------
if [ -x "venv/bin/python" ]; then
    PY="venv/bin/python"
    ETIQUETTE="environnement isole du dossier"
elif [ -x "/usr/bin/python3" ]; then
    PY="/usr/bin/python3"
    ETIQUETTE="Python d'Apple (secours)"
else
    echo "Aucun Python utilisable n'a ete trouve."
    echo "Consultez FICHE-RETOUR-ARRIERE.md, section « Si DFM ne demarre plus du tout »."
    echo
    read -n 1 -s -r -p "Appuyez sur une touche pour fermer..."
    exit 1
fi

VERSION="$("$PY" -V 2>&1)"

echo "───────────────────────────────────────────────"
echo "  DFM — Dental Formation Manager"
echo "───────────────────────────────────────────────"
echo "  $VERSION  ·  $ETIQUETTE"
echo "  Adresse : http://127.0.0.1:$PORT"
echo
echo "  Pour arreter DFM : Ctrl + C dans cette fenetre."
echo "  Si vous fermez la fenetre sans Ctrl + C, relancez"
echo "  simplement ce lanceur : il fera le menage."
echo "───────────────────────────────────────────────"
echo

( sleep 3; open "http://127.0.0.1:$PORT" ) &

# ON PASSE PAR servir.py DEPUIS LE 19/08/2026. « app.py » lance le serveur de
# developpement de Flask, qui l'annonce lui-meme : « do not use in a production
# deployment ». servir.py met waitress devant, refuse de demarrer sans mot de
# passe des qu'il ecoute ailleurs qu'ici, et lance le planificateur.
#
# C'EST LE MEME FICHIER QUE SUR UN SERVEUR. Ce qui marche chez vous marchera
# la-bas : on ne decouvre pas le jour du demenagement que le demarrage differe.
if [ -f "servir.py" ]; then
    "$PY" servir.py
else
    "$PY" app.py
fi
CODE=$?

# ---------- 3. menage a la sortie ----------
# Flask en mode debug lance un processus enfant qui peut survivre au parent.
RESTE="$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | sort -u)"
for P in $RESTE; do kill "$P" 2>/dev/null; done

echo
if [ $CODE -ne 0 ] && [ $CODE -ne 130 ]; then
    echo "DFM s'est arrete avec une erreur (code $CODE)."
    echo "Le message ci-dessus en donne la cause."
    echo "En cas de doute : FICHE-RETOUR-ARRIERE.md, dans ce meme dossier."
else
    echo "DFM est arrete."
fi
echo
read -n 1 -s -r -p "Appuyez sur une touche pour fermer cette fenetre..."
