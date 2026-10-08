#!/bin/bash
# Voir les sauvegardes du serveur, en prendre une, ou en verifier une.
#
# LE PASSAGE AUTOMATIQUE A LIEU CHAQUE NUIT A 3H30 : ce lanceur ne sert qu'a
# regarder, ou a prendre un instantane avant une operation delicate.
cd "$(dirname "$0")"
clear
echo
echo "  ┌──────────────────────────────────────────────────────────────┐"
echo "  │  SAUVEGARDES DE DFM                                          │"
echo "  └──────────────────────────────────────────────────────────────┘"
echo
echo "  1  voir les sauvegardes existantes"
echo "  2  prendre une sauvegarde maintenant"
echo "  3  verifier qu'une sauvegarde se restaure (sans rien remplacer)"
echo
printf "  Votre choix [1] : "
read -r CHOIX
echo
case "$CHOIX" in
  2) ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 \
       'cd /home/dfm/DFM && venv/bin/python sauvegarde.py' ;;
  3)
    ssh -o ConnectTimeout=20 dfm@163.172.8.49 \
      'cd /home/dfm/DFM && venv/bin/python restaurer.py --liste'
    printf "  Laquelle (copiez son nom) : "
    read -r QUOI
    echo
    ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 \
      "cd /home/dfm/DFM && venv/bin/python restaurer.py '$QUOI'"
    echo
    echo "  La copie d'essai reste sur le serveur ; elle peut etre effacee."
    ;;
  *) ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 \
       'cd /home/dfm/DFM && venv/bin/python sauvegarde.py --liste' ;;
esac
echo
echo "  Vous pouvez fermer cette fenetre."
echo
