#!/bin/bash
# Ouvre une session sur le serveur et gere les comptes de DFM.
#
# POURQUOI PASSER PAR ICI PLUTOT QUE PAR L'ECRAN. L'ecran « Comptes » est
# derriere la connexion : il faut deja etre entre pour s'en servir. Cette porte
# de service sert a deux moments ou personne ne peut ouvrir de l'interieur —
# la creation du tout premier compte, et le mot de passe perdu du dernier
# gerant. Elle demande un acces au serveur, ce qui est la bonne barriere.
cd "$(dirname "$0")"
clear
echo
echo "  ┌──────────────────────────────────────────────────────────────┐"
echo "  │  LES COMPTES DE DFM                                          │"
echo "  └──────────────────────────────────────────────────────────────┘"
echo
echo "  1  voir les comptes existants"
echo "  2  creer un compte"
echo "  3  changer le mot de passe de quelqu'un"
echo
printf "  Votre choix [1] : "
read -r CHOIX
echo
case "$CHOIX" in
  2)
    echo "  Le mot de passe se tape SANS RIEN S'AFFICHER — c'est normal."
    echo "  Dix caracteres au minimum."
    echo
    ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 \
      'cd /home/dfm/DFM && venv/bin/python utilisateur.py --creer'
    ;;
  3)
    printf "  Identifiant du compte a changer : "
    read -r QUI
    echo
    ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 \
      "cd /home/dfm/DFM && venv/bin/python utilisateur.py --mot-de-passe '$QUI'"
    ;;
  *)
    ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 \
      'cd /home/dfm/DFM && venv/bin/python utilisateur.py'
    ;;
esac
echo
echo "  Vous pouvez fermer cette fenetre."
echo
