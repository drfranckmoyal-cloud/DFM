#!/bin/bash
# Rapatrie les derniers fichiers qui ne vivent encore que dans le Drive Google.
# Double-cliquez ce fichier depuis le Finder.
#
# IL VIT A COTE DE DFM.command, dans le dossier du projet, et non plus sur le
# bureau : un lanceur pose sur le bureau disparait au premier rangement.
#
# CE LANCEUR FAIT LES DEUX GESTES A LA SUITE :
#   1. si aucune autorisation Google n'est en place, une page de connexion
#      s'ouvre dans le navigateur — CHOISISSEZ LE COMPTE QUI POSSEDE VOS
#      DOCUMENTS DE FORMATION, pas votre compte personnel ;
#   2. il descend les pieces manquantes sur le disque.
#
# IL NE MODIFIE NI NE SUPPRIME RIEN, ni chez vous ni dans le Drive : il ne fait
# que copier vers votre ordinateur.

cd "$(dirname "$0")" || exit 1

if [ -x "venv/bin/python" ]; then
    PY="venv/bin/python"
elif [ -x "/usr/bin/python3" ]; then
    PY="/usr/bin/python3"
else
    echo "Aucun Python utilisable n'a ete trouve."
    echo
    read -n 1 -s -r -p "Appuyez sur une touche pour fermer..."
    exit 1
fi

clear
echo "───────────────────────────────────────────────────────────────"
echo "  DFM — Rapatriement des dernieres pieces du Drive"
echo "───────────────────────────────────────────────────────────────"
echo
if [ ! -f "token.json" ]; then
    echo "  Aucune autorisation Google en place : une page de connexion"
    echo "  va s'ouvrir dans le navigateur."
    echo
    echo "  ATTENTION AU COMPTE. Choisissez celui qui possede vos"
    echo "  documents de formation — programmes, reglements, RIB."
    echo "  Ce n'est pas forcement celui que Google propose en premier."
else
    echo "  Une autorisation Google est deja en place."
    echo "  Si le rapatriement echoue sur TOUTES les pieces, c'est qu'elle"
    echo "  ouvre le Drive du mauvais compte : le message vous le dira."
fi
echo
echo "  Rien n'est modifie ni supprime : on ne fait que copier."
echo "───────────────────────────────────────────────────────────────"
echo

"$PY" rapatrier_pieces.py
CODE=$?

echo
echo "───────────────────────────────────────────────────────────────"
if [ $CODE -eq 0 ]; then
    echo "  Termine. Toutes les pieces sont sur votre ordinateur."
    echo "  Vous n'aurez plus a relancer ce lanceur."
else
    echo "  Certaines pieces n'ont pas pu etre descendues."
    echo "  Le detail ci-dessus dit laquelle des trois causes est en jeu."
fi
echo "───────────────────────────────────────────────────────────────"
echo
read -n 1 -s -r -p "Appuyez sur une touche pour fermer cette fenetre..."
