#!/bin/bash
# Ouvre une session sur le serveur DFM et lance la pose du mot de passe.
# Le mot de passe ne passe par aucun fichier : il est tape ici, transforme en
# empreinte sur le serveur, et l'original n'est jamais ecrit nulle part.
cd "$(dirname "$0")"
clear
echo
echo "  ┌──────────────────────────────────────────────────────────────┐"
echo "  │  MOT DE PASSE DE DFM EN LIGNE                                │"
echo "  └──────────────────────────────────────────────────────────────┘"
echo
echo "  Tapez votre mot de passe deux fois. RIEN NE S'AFFICHE pendant la"
echo "  frappe — c'est normal, les caracteres sont masques. Tapez, puis"
echo "  appuyez sur Entree."
echo
echo "  Dix caracteres au minimum. C'est la seule barriere devant vos"
echo "  181 contacts, vos conventions signees et vos factures."
echo
ssh -t -o ConnectTimeout=20 dfm@163.172.8.49 'cd /home/dfm/DFM && venv/bin/python mot_de_passe.py'
echo
echo "  Vous pouvez fermer cette fenetre."
echo
